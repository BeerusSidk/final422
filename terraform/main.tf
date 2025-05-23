# Provider Configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}


#####
#service account#
##########
resource "google_service_account" "flask_vm_sa" {
  account_id   = "flask-vm-sa"
  display_name = "Flask VM Service Account"
}

#####
#IAM#
#####

resource "google_project_iam_member" "flask_sa_sql_access" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.flask_vm_sa.email}"
}

resource "google_project_iam_member" "flask_sa_storage_access" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.flask_vm_sa.email}"
}

resource "google_project_iam_member" "flask_sa_network_access" {
  project = var.project_id
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${google_service_account.flask_vm_sa.email}"
}

#########
# VPC Resources
#########

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
  region        = var.region  
  private_ip_google_access = true
}

resource "google_compute_global_address" "private-ip-range" {
  name          = "private-ip-range"
  purpose       = "VPC_PEERING"         
  address_type  = "INTERNAL"
  prefix_length = 16                   
  network       = google_compute_network.finalexam422_vpc.id
}

resource "google_service_networking_connection" "private_services_connection" {
  network                  = google_compute_network.finalexam422_vpc.name
  service                   = "servicenetworking.googleapis.com"  
  reserved_peering_ranges   = [google_compute_global_address.private-ip-range.name]

  depends_on = [google_compute_global_address.private-ip-range]
}



#########
# Firewall Resources
#########

# Firewall Rule For Users to Access the App
resource "google_compute_firewall" "flask-app-firewall" {
  name    = "flask-app-firewall"
  network = google_compute_network.finalexam422_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22", "80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]  # Allow from any IP
}


##########
# Storage Resources
##########

resource "google_storage_bucket" "finalexam422_bucket" {
  name         = var.storage_bucket_name
  location     = "US"
  storage_class = "STANDARD"
  force_destroy = true
}

# Storage Permissions
resource "google_project_iam_member" "vm_storage_access" {
  project = var.project_id
  member  = "serviceAccount:${google_service_account.flask_vm_sa.email}"
  role    = "roles/storage.objectAdmin"
}

##########
# Cloud SQL MySQL Instance
##########

resource "google_sql_database_instance" "finalexam422_mysql_instance" {
  name             = "finalexam422-mysql-instance"
  region           = var.region
  database_version = "MYSQL_8_0" 

  root_password = var.db_password

  deletion_protection = false

  depends_on = [google_service_networking_connection.private_services_connection]

  settings {
    tier = "db-n1-standard-1"
    backup_configuration {
      enabled = true
      start_time = "03:00"
    }
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.finalexam422_vpc.id  
        psc_config {
            psc_enabled = true
      }
    }
  }
}

resource "google_sql_database" "finalexam422_database" {
  name     = var.db_name
  instance = google_sql_database_instance.finalexam422_mysql_instance.name
}

resource "google_sql_user" "finalexam422_user" {
  name     = "${var.db_user}" 
  instance = google_sql_database_instance.finalexam422_mysql_instance.name
  password = var.db_password
}

##########
# VM for Flask App
##########

resource "google_compute_instance" "flask_vm" {
  name         = "flask-app-vm"
  machine_type = "e2-standard-2"
  zone         = var.zone
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
    email  = google_service_account.flask_vm_sa.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    apt-get update
    sudo apt-get install -y python3-pip python3-dev
    sudo apt-get install -y git

    git clone https://github.com/BeerusSidk/final422.git /home/duckhoi311/final
    cd /home/duckhoi311/final

    git checkout master

    sudo pip3 install -r requirements.txt

    # Set up environment variables for the Flask app

    echo "INSTANCE_CONNECTION_NAME=\"${google_sql_database_instance.finalexam422_mysql_instance.connection_name}\"" >> /home/duckhoi311/final422/.env
    echo "DB_USER=\"${var.db_user}\"" >> /home/duckhoi311/final422/.env
    echo "DB_PASSWORD=\"${var.db_password}\"" >> /home/duckhoi311/final422/.env
    echo "DB_NAME=\"${var.db_name}\"" >> /home/duckhoi311/final422/.env
    echo "GOOGLE_CLOUD_PROJECT=\"${var.project_id}\"" >> /home/duckhoi311/final422/.env
    echo "STORAGE_NAME=\"${google_storage_bucket.finalexam422_bucket.name}\"" >> /home/duckhoi311/final422/.env
    echo "PORT=\"${var.port}\"" >> /home/duckhoi311/final422/.env
    echo "SECRET_KEY=\"$(openssl rand -hex 32)\"" >> /home/duckhoi311/final422/.env

    python3 init/init.py

    # Start the Flask app using Gunicorn
    sudo -E gunicorn -b :$PORT app:app &
  EOT
}
