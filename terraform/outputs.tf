# outputs.tf

##########
# Output for Flask VM Public IP
##########
output "flask_vm_public_ip" {
  description = "The public IP of the Flask VM."
  value       = google_compute_instance.flask_vm.network_interface[0].access_config[0].nat_ip
}

##########
# Output for Storage Bucket Name
##########
output "storage_bucket_name" {
  description = "The name of the storage bucket."
  value       = google_storage_bucket.finalexam422_bucket.name
}

##########
# Output for MySQL Instance Connection Name
##########
output "mysql_instance_connection_name" {
  description = "The connection name for the MySQL instance."
  value       = google_sql_database_instance.finalexam422_mysql_instance.connection_name
}

##########
# Output for Cloud SQL Database Name
##########
output "mysql_database_name" {
  description = "The name of the MySQL database."
  value       = google_sql_database.finalexam422_database.name
}


##########
# Output for Cloud SQL Database User Credentials
##########
output "mysql_db_user" {
  description = "The MySQL database user."
  value       = google_sql_user.finalexam422_user.name
}

##########
# Output for VM Service Account Email
##########
output "vm_service_account_email" {
  description = "The service account email used by the VM."
  value       = var.service_account_email
}

##########
# Output for Project ID
##########
output "project_id" {
  description = "The project ID for the GCP resources."
  value       = var.project_id
}

##########
# Output for Flask App Port
##########
output "flask_app_port" {
  description = "The port used by the Flask app."
  value       = var.port
}
