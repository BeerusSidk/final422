# Set up Google Cloud Project
provider "google" {
    project = "finalexam422-459623"
    region = "us-central1"
    zone = "us-central1-c"
}

#######
# VPC #
#######

# VPC
resource "google_compute_network" "finalexam422_vpc" {
  name                    = "finalexam422-vpc"
  auto_create_subnetworks = false  
}

# Subnet
resource "google_compute_subnetwork" "finalexam422_subnet" {
  name          = "finalexam422-subnet"
  network       = google_compute_network.finalexam422_vpc.name  
  ip_cidr_range = "10.0.0.0/16"  
  region        = "us-central1"  
}
           

#################
# FireWall Rule #
#################

# Firewall Rule For Users to access the App
resource "google_compute_firewall" "flask-app-firewall" {
  name    = "flask-app-firewall"
  network = google_compute_network.finalexam422_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443"]  # Allow HTTP (port 80) and HTTPS (port 443)
  }

  source_ranges = ["0.0.0.0/0"]  # Allow from whatever IP addresses
}

######################
# Storage and bucket #
######################

resource "google_storage_bucket" "finalexam422_bucket" {
  name = "finalexam422-bucket"
  location = "US"
  storage_class = "STANDARD"
}

#STORAGE PERMISSION
resource "google_project_iam_member" "vm_storage_access" {
  project = "finalexam422-459623"
  member  = "serviceAccount:1020535552160-compute@developer.gserviceaccount.com"
  role    = "roles/storage.objectAdmin"  # Grants access to Cloud Storage
}


############################
# Cloud SQL MySQL Instance #
############################

resource "google_sql_database_instance" "finalexam422_mysql_instance" {
  name             = "finalexam422-mysql-instance"
  region           = "us-central1"
  database_version = "MYSQL_8_0" 

  root_password = "haitrang76"  #hardcode for now

  deletion_protection = false

  settings {
    tier = "db-n1-standard-1"
    backup_configuration {
      enabled = true
      start_time = "03:00"
    }
    ip_configuration {
        ipv4_enabled = true

        authorized_networks {
          name  = "flask-vm-public-ip"
          value = google_compute_instance.flask_vm.network_interface[0].access_config[0].nat_ip
      }
    }
  }
}


# Create MySQL Database
resource "google_sql_database" "finalexam422_database" {
    name     = "finalexam422-database"
    instance = google_sql_database_instance.finalexam422_mysql_instance.name
    
}

# Create MySQL User
resource "google_sql_user" "finalexam422_user" {
  name     = "app_user"
  instance = google_sql_database_instance.finalexam422_mysql_instance.name
  password = "haitrang76"       #hardcode for now
}


###################
# VM for Flask App #
###################

# Compute Engine VM
resource "google_compute_instance" "flask_vm" {
  name         = "flask-app-vm"
  machine_type = "e2-standard-2"
  zone         = "us-central1-c"
  tags         = ["vm-instance"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network    = google_compute_network.finalexam422_vpc.name
    subnetwork = google_compute_subnetwork.finalexam422_subnet.name
    access_config {}
  }

  service_account {
    email  = "1020535552160-compute@developer.gserviceaccount.com"
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update
    apt-get install -y python3-pip python3-dev
    apt-get install -y git

    # Clone the Flask app repository (replace with your actual repository)p
    cd /home/duckhoi311
    git clone https://github.com/BeerusSidk/tempFinal422.git
    cd tempFinal422/SE4220_Project5/photogallery

    #revert back to the project4 commit
    git checkout project4

    # Install Python dependencies
    sudo pip3 install -r requirements.txt

    # Set up environment variables for the Flask app
    export INSTANCE_CONNECTION_NAME="finalexam422-459623:us-central1:finalexam422-mysql-instance"
    export DB_USER="app_user"  

    export DB_PASSWORD="haitrang76" 
    export DB_NAME="finalexam422-database" 
    export FLASK_ENV="production"
    export GOOGLE_CLOUD_PROJECT="finalexam422-459623"
    export STORAGE_NAME="${google_storage_bucket.finalexam422_bucket.name}"
    export PORT=80

    python3 init/init.py

    # Start the Flask app using Gunicorn
   sudo -E gunicorn -b :$PORT app:app &
  EOT
}


