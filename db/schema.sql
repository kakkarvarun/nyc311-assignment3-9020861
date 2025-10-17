CREATE DATABASE IF NOT EXISTS nyc311 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE nyc311;

CREATE TABLE IF NOT EXISTS ingestion_log (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  month_key CHAR(7) NOT NULL,              -- 'YYYY-MM'
  source_file VARCHAR(255) NOT NULL,
  row_count BIGINT UNSIGNED DEFAULT 0,
  started_at TIMESTAMP NULL,
  finished_at TIMESTAMP NULL,
  status ENUM('started','success','failed') NOT NULL,
  details JSON NULL,
  UNIQUE KEY uq_month (month_key)
);

CREATE TABLE IF NOT EXISTS service_requests (
  request_id BIGINT UNSIGNED NOT NULL,     -- "Unique Key"
  created_datetime DATETIME NOT NULL,
  closed_datetime DATETIME NULL,
  agency VARCHAR(16) NULL,
  agency_name VARCHAR(128) NULL,
  complaint_type VARCHAR(128) NOT NULL,
  descriptor VARCHAR(255) NULL,
  borough VARCHAR(32) NOT NULL,
  city VARCHAR(128) NULL,
  latitude DECIMAL(9,6) NULL,
  longitude DECIMAL(9,6) NULL,
  status VARCHAR(64) NULL,
  resolution_description TEXT NULL,
  month_key CHAR(7) NOT NULL,              -- from created_datetime
  PRIMARY KEY (request_id)
);

-- Indexes aligned to filters
CREATE INDEX idx_created_datetime ON service_requests (created_datetime);
CREATE INDEX idx_borough_type_date ON service_requests (borough, complaint_type, created_datetime);
