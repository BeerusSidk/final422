# variables.tf

variable "project_id" {
  description = "The GCP project ID."
  type        = string
  default     = "finalexam422-459623"
}

variable "region" {
  description = "The region in which the resources will be created."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The zone in which the VM will be created."
  type        = string
  default     = "us-central1-c"
}

variable "storage_bucket_name" {
  description = "The name of the Google Cloud Storage bucket."
  type        = string
  default     = "finalexam422-bucket"
}

variable "instance_connection_name" {
  description = "The instance connection name for Cloud SQL."
  type        = string
  default     = "finalexam422-459623:us-central1:finalexam422-mysql-instance"
}

variable "db_name" {
  description = "The name of the MySQL database."
  type        = string
  default     = "finalexam422-database"
}

variable "db_password" {
  description = "The password for the MySQL root user."
  type        = string
  default     = "haitrang76"
}

# New port variable
variable "port" {
  description = "Port number for the Flask app."
  type        = number
  default     = 80  # Default to port 80
}

# New service account email variable
variable "service_account_email" {
  description = "The service account email to be used for the VM."
  type        = string
  default     = "1020535552160-compute@developer.gserviceaccount.com"
}

variable "sql_instance_name" {
    description = "The connection name of the SQL instance"
    type = string
    default = "finalexam422-459623:us-central1:finalexam422-mysql-instance"
}

variable "db_user" {
    description = "The user of the database"
    type = string
    default = "app_user"
}