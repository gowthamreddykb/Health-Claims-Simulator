-- =====================================================================
-- HEALTH INSURANCE CLAIMS PROCESSING PLATFORM - MYSQL DDL SCHEMA
-- Compatible with MySQL 8.0+ and MariaDB 10.5+
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `health_insurance_claims` 
  DEFAULT CHARACTER SET utf8mb4 
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `health_insurance_claims`;

-- Drop existing tables in reverse dependency order to prevent FK violations
DROP TABLE IF EXISTS `settlements`;
DROP TABLE IF EXISTS `claim_history`;
DROP TABLE IF EXISTS `claim_documents`;
DROP TABLE IF EXISTS `claims`;
DROP TABLE IF EXISTS `members`;
DROP TABLE IF EXISTS `policies`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `plans`;
DROP TABLE IF EXISTS `hospitals`;

-- 1. HOSPITALS
CREATE TABLE `hospitals` (
  `hospital_id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(150) NOT NULL,
  `city` VARCHAR(100) NOT NULL,
  `network_status` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1 = Network, 0 = Non-Network',
  PRIMARY KEY (`hospital_id`),
  INDEX `idx_hospitals_network` (`network_status`),
  INDEX `idx_hospitals_city` (`city`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. PLANS
CREATE TABLE `plans` (
  `plan_id` INT NOT NULL AUTO_INCREMENT,
  `plan_name` VARCHAR(100) NOT NULL,
  `covered_treatment_types` VARCHAR(120) NOT NULL COMMENT 'Pipe-separated e.g. inpatient|daycare',
  `annual_limit_inr` DECIMAL(12,2) NOT NULL,
  `deductible_inr` DECIMAL(10,2) NOT NULL,
  `copay_percent` DECIMAL(5,2) NOT NULL,
  PRIMARY KEY (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. USERS
CREATE TABLE `users` (
  `user_id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(80) NOT NULL,
  `display_name` VARCHAR(120) NOT NULL,
  `role` VARCHAR(30) NOT NULL COMMENT 'policyholder, hospital, claims_officer, admin',
  `hospital_id` INT NULL DEFAULT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uq_users_username` (`username`),
  INDEX `idx_users_role` (`role`),
  INDEX `idx_users_hospital` (`hospital_id`),
  CONSTRAINT `fk_users_hospital` FOREIGN KEY (`hospital_id`) REFERENCES `hospitals` (`hospital_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. POLICIES
CREATE TABLE `policies` (
  `policy_id` INT NOT NULL AUTO_INCREMENT,
  `holder_user_id` INT NOT NULL,
  `plan_id` INT NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `status` VARCHAR(30) NOT NULL DEFAULT 'active' COMMENT 'active, expired, cancelled',
  PRIMARY KEY (`policy_id`),
  INDEX `idx_policies_holder` (`holder_user_id`),
  INDEX `idx_policies_plan` (`plan_id`),
  INDEX `idx_policies_status` (`status`),
  CONSTRAINT `fk_policies_holder` FOREIGN KEY (`holder_user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_policies_plan` FOREIGN KEY (`plan_id`) REFERENCES `plans` (`plan_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. MEMBERS
CREATE TABLE `members` (
  `member_id` INT NOT NULL AUTO_INCREMENT,
  `policy_id` INT NOT NULL,
  `display_name` VARCHAR(120) NOT NULL,
  `relationship` VARCHAR(50) NOT NULL COMMENT 'self, spouse, child, parent',
  PRIMARY KEY (`member_id`),
  INDEX `idx_members_policy` (`policy_id`),
  CONSTRAINT `fk_members_policy` FOREIGN KEY (`policy_id`) REFERENCES `policies` (`policy_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. CLAIMS
CREATE TABLE `claims` (
  `claim_id` INT NOT NULL AUTO_INCREMENT,
  `policy_id` INT NOT NULL,
  `member_id` INT NOT NULL,
  `hospital_id` INT NOT NULL,
  `claim_type` VARCHAR(30) NOT NULL COMMENT 'cashless, reimbursement',
  `treatment_type` VARCHAR(50) NOT NULL COMMENT 'inpatient, daycare',
  `admission_date` DATE NOT NULL,
  `discharge_date` DATE NOT NULL,
  `requested_amount_inr` DECIMAL(12,2) NOT NULL,
  `status` VARCHAR(30) NOT NULL DEFAULT 'draft' COMMENT 'draft, submitted, in_review, more_info, approved, rejected, paid',
  `eligible_amount_inr` DECIMAL(12,2) NULL DEFAULT NULL,
  `officer_user_id` INT NULL DEFAULT NULL,
  `payment_recorded_date` DATE NULL DEFAULT NULL,
  `description` TEXT NULL DEFAULT NULL,
  `decision_reason` TEXT NULL DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `submitted_at` DATETIME NULL DEFAULT NULL,
  PRIMARY KEY (`claim_id`),
  INDEX `idx_claims_policy_status` (`policy_id`, `status`),
  INDEX `idx_claims_officer_status` (`officer_user_id`, `status`),
  INDEX `idx_claims_hospital` (`hospital_id`),
  INDEX `idx_claims_status` (`status`),
  CONSTRAINT `fk_claims_policy` FOREIGN KEY (`policy_id`) REFERENCES `policies` (`policy_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_claims_member` FOREIGN KEY (`member_id`) REFERENCES `members` (`member_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_claims_hospital` FOREIGN KEY (`hospital_id`) REFERENCES `hospitals` (`hospital_id`) ON DELETE RESTRICT,
  CONSTRAINT `fk_claims_officer` FOREIGN KEY (`officer_user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. CLAIM DOCUMENTS
CREATE TABLE `claim_documents` (
  `claim_id` INT NOT NULL,
  `document_type` VARCHAR(50) NOT NULL COMMENT 'hospital_bill, discharge_summary',
  `checklist_status` VARCHAR(30) NOT NULL DEFAULT 'received' COMMENT 'received, missing',
  PRIMARY KEY (`claim_id`, `document_type`),
  CONSTRAINT `fk_documents_claim` FOREIGN KEY (`claim_id`) REFERENCES `claims` (`claim_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. CLAIM HISTORY
CREATE TABLE `claim_history` (
  `claim_id` INT NOT NULL,
  `sequence_no` INT NOT NULL,
  `from_status` VARCHAR(30) NULL DEFAULT NULL,
  `to_status` VARCHAR(30) NOT NULL,
  `actor_user_id` INT NOT NULL,
  `note` TEXT NULL DEFAULT NULL,
  `event_date` DATE NOT NULL,
  PRIMARY KEY (`claim_id`, `sequence_no`),
  INDEX `idx_claim_history_lookup` (`claim_id`, `event_date`),
  CONSTRAINT `fk_history_claim` FOREIGN KEY (`claim_id`) REFERENCES `claims` (`claim_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_history_actor` FOREIGN KEY (`actor_user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. SETTLEMENTS
CREATE TABLE `settlements` (
  `claim_id` INT NOT NULL,
  `payee_type` VARCHAR(30) NOT NULL COMMENT 'hospital, policyholder',
  `amount_inr` DECIMAL(12,2) NOT NULL,
  `recorded_by_user_id` INT NOT NULL,
  `recorded_date` DATE NOT NULL,
  PRIMARY KEY (`claim_id`),
  INDEX `idx_settlements_recorder` (`recorded_by_user_id`),
  INDEX `idx_settlements_date` (`recorded_date`),
  CONSTRAINT `fk_settlements_claim` FOREIGN KEY (`claim_id`) REFERENCES `claims` (`claim_id`) ON DELETE CASCADE,
  CONSTRAINT `fk_settlements_recorder` FOREIGN KEY (`recorded_by_user_id`) REFERENCES `users` (`user_id`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
