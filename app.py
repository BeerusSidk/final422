import os
from google.cloud.sql.connector import Connector
import pymysql
import io
from urllib.parse import urlparse
from google.cloud import storage
from flask import (
    Flask, render_template, redirect, url_for, request, session, flash, g, abort, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

##############################################################################
# GOOGLE CLOUD BUCKET CONFIG
##############################################################################
bucketName = os.getenv('STORAGE_NAME')

def upload_to_gcs(file, filename):
    client = storage.Client()
    bucket = client.bucket(bucketName)
    blob = bucket.blob(filename)
    blob.upload_from_file(file, content_type=file.content_type)
    # Optional: make public
    blob.make_public()
    return blob.public_url



##############################################################################
# FLASK CONFIG
##############################################################################
app = Flask(__name__)

# Configure where uploaded files are stored
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure folder exists

# Allowed extensions for image uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

##############################################################################
# DATABASE CONFIG (Adjust to your Cloud SQL credentials)
##############################################################################
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")
CLOUD_SQL_PUBLIC_IP = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")                # Your DB username
DB_PASSWORD = os.getenv("DB_PASSWORD")          # Your DB password
DB_NAME = os.getenv("DB_NAME")    # Make sure this matches your DB name exactly 
connector = Connector()
##############################################################################
# DATABASE CONNECTION HELPERS
##############################################################################
def get_db():
    connection = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pymysql",
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

@app.teardown_appcontext
def teardown_db(exception):
    """
    Closes the DB connection at the end of each request if it exists.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()



@app.route('/printenv')
def printenv():
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>Database Configuration</title>
    </head>
    <body>
      <h1>Database Configuration</h1>
      <ul>
        <li><strong>INSTANCE_CONNECTION_NAME:</strong> {os.getenv("INSTANCE_CONNECTION_NAME")}</li>
        <li><strong>CLOUD_SQL_PUBLIC_IP:</strong> {os.getenv("DB_HOST")}</li>
        <li><strong>DB_USER:</strong> {os.getenv("DB_USER")}</li>
        <li><strong>DB_PASSWORD:</strong> {os.getenv("DB_PASSWORD")}</li>
        <li><strong>DB_NAME:</strong> {os.getenv("DB_NAME")}</li>
      </ul>
    </body>
    </html>
    """

@app.route('/check-conn')
def check_conn():
    try:
        conn = get_db()  # your function to get DB connection
        if conn is None:
            status = "Connection not initialized."
        else:
            status = "Connection successful."
    except Exception as e:
        status = f"Error connecting: {e}"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><title>DB Connection Status</title></head>
    <body>
      <h1>Database Connection Status</h1>
      <p>{status}</p>
    </body>
    </html>
    """


##############################################################################
# HELPER FUNCTIONS
##############################################################################
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

##############################################################################
# ROUTES
##############################################################################
@app.route('/')
def index():
    """
    If the user is logged in, render the gallery of their photos;
    otherwise, redirect to login.
    """
    if 'username' in session:
        conn = get_db()
        cur = conn.cursor()
        # Retrieve photos for the current logged-in user
        cur.execute("""
            SELECT id, filename, title, upload_time
            FROM photos
            WHERE user_id = %s
            ORDER BY upload_time DESC
        """, (session['user_id'],))
        photos = cur.fetchall()
        return render_template('gallery.html', photos=photos)
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 1. Get form data
        username = request.form.get('username')
        password = request.form.get('password')

        # 2. Check credentials against DB
        conn = get_db()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user_row = cur.fetchone()
        

        if user_row:
            stored_hash = user_row['password_hash']
            # Check the password against the hash
            if check_password_hash(stored_hash, password):
                # Correct password -> log the user in
                session['username'] = username
                session['user_id'] = user_row['id']
                return redirect(url_for('index'))
        
        # If we reach here, login failed
        flash("Invalid credentials", "error")

    # GET request or failed login -> show login form
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # 1. Get form data
        username = request.form.get('username')
        password = request.form.get('password')

        # 2. Check if username is taken
        try:
            conn = get_db()
            
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            existing_user = cur.fetchone()
            if existing_user:
                flash("Username already taken!", "error")
                return redirect(url_for('signup'))
            
            # 3. Insert new user
            hashed_pass = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, hashed_pass)
            )
            conn.commit()

            flash("Signup successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            return f"""
                    <!DOCTYPE html>
                    <html lang="en">
                    <head><title>DB Connection Status</title></head>
                    <body>
                    <h1>Database Connection Status</h1>
                    <p>{status}</p>
                    </body>
                    </html>
                    """

    # If GET request -> show signup form
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


@app.route('/upload', methods=['GET', 'POST'])
def upload_photo():
    """
    CREATE: Upload a new photo file and insert a record in the DB.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')  # if your form includes a title field
        file = request.files.get('photo')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_url = upload_to_gcs(file, filename)

            # Insert into database
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO photos (user_id, filename, title)
                VALUES (%s, %s, %s)
            """, (session['user_id'], file_url, title))
            conn.commit()

            flash("Photo uploaded successfully!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid file or no file selected.", "error")

    return render_template('upload.html')


@app.route('/download/<int:photo_id>')
def download(photo_id):
    """
    READ: Download (send_file) a photo by its ID (belongs to the logged-in user).
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT title, filename, user_id FROM photos WHERE id=%s", (photo_id,))
    photo = cur.fetchone()

    if not photo:
        abort(404)
    if photo['user_id'] != session.get('user_id'):
        abort(403)  # user is not allowed to download someone else's photo

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucketName)
    parsed_url = urlparse(photo['filename'])
    clean_filename = os.path.basename(parsed_url.path)
    blob = bucket.blob(clean_filename)

    # Download the blob into memory
    file_data = blob.download_as_bytes()

    # Stream the file back to the client
    return send_file(
        io.BytesIO(file_data),
        as_attachment=True,
        download_name=f"{photo['title']}{os.path.splitext(clean_filename)[1]}",
        mimetype='application/octet-stream')


@app.route('/delete/<int:photo_id>')
def delete_photo(photo_id):
    """
    DELETE: Remove a photo record from DB and delete the file from disk.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT filename, user_id FROM photos WHERE id=%s", (photo_id,))
    photo = cur.fetchone()

    if photo and photo['user_id'] == session.get('user_id'):
        # Delete file from filesystem
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete DB record
        cur.execute("DELETE FROM photos WHERE id=%s", (photo_id,))
        conn.commit()
        flash("Photo deleted.", "info")
    else:
        flash("Photo not found or not yours to delete.", "error")

    return redirect(url_for('index'))


@app.route('/edit/<int:photo_id>', methods=['GET', 'POST'])
def edit_photo(photo_id):
    """
    UPDATE: (Optional) Let user change the title of their photo.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()

    # Fetch the photo to ensure it belongs to the user
    cur.execute("SELECT id, title, filename, user_id FROM photos WHERE id=%s", (photo_id,))
    photo = cur.fetchone()
    if not photo or photo['user_id'] != session['user_id']:
        flash("Photo not found or you don't own it.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_title = request.form.get('title')
        # Update the database
        cur.execute("UPDATE photos SET title=%s WHERE id=%s", (new_title, photo_id))
        conn.commit()
        flash("Photo updated successfully!", "success")
        return redirect(url_for('index'))

    # If GET request, show edit form
    return render_template('edit_photo.html', photo=photo)


@app.route('/search')
def search():
    """
    READ: Search for photos by title for the logged-in user.
    """
    if 'username' not in session:
        return redirect(url_for('login'))

    query = request.args.get('q', '').strip()

    conn = get_db()
    cur = conn.cursor()
    if query:
        # Find photos whose title contains the query string
        cur.execute("""
            SELECT id, filename, title, upload_time
            FROM photos
            WHERE user_id = %s
              AND title LIKE %s
            ORDER BY upload_time DESC
        """, (session['user_id'], f"%{query}%"))
        results = cur.fetchall()
    else:
        results = []

    return render_template('search.html', query=query, results=results)

##############################################################################
# LAUNCH APP
##############################################################################
if __name__ == '__main__':
    app.run(debug=True)
