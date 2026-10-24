-- =====================================================================
-- HEALTH INSURANCE CLAIMS PROCESSING PLATFORM - SEED DATA SCRIPT
-- =====================================================================

USE `health_insurance_claims`;

-- 1. HOSPITALS
INSERT INTO `hospitals` (`hospital_id`, `name`, `city`, `network_status`) VALUES
(1, 'CityCare Hospital', 'Puttaparthi', 1),
(2, 'Lotus Medical Centre', 'Anantapur', 1),
(3, 'Green Valley Hospital', 'Kadiri', 0),
(4, 'Sunrise Hospital', 'Dharmavaram', 1),
(5, 'Riverbend Clinic', 'Hindupur', 0);

-- 2. PLANS
INSERT INTO `plans` (`plan_id`, `plan_name`, `covered_treatment_types`, `annual_limit_inr`, `deductible_inr`, `copay_percent`) VALUES
(1, 'Essential Care', 'inpatient', 100000.00, 2000.00, 10.00),
(2, 'Plus Care', 'inpatient|daycare', 200000.00, 1000.00, 5.00),
(3, 'Family Care', 'inpatient|daycare', 300000.00, 1500.00, 10.00);

-- 3. USERS (Default Password: Password123!)
INSERT INTO `users` (`user_id`, `username`, `display_name`, `role`, `hospital_id`, `password_hash`, `created_at`) VALUES
(1, 'aasha', 'Aasha Rao', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(2, 'bilal', 'Bilal Khan', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(3, 'chitra', 'Chitra Devi', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(4, 'dev', 'Dev Kumar', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(5, 'esha', 'Esha Reddy', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(6, 'farhan', 'Farhan Ali', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(7, 'gita', 'Gita Naik', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(8, 'harish', 'Harish Babu', 'policyholder', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(9, 'city_hospital', 'CityCare Desk', 'hospital', 1, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(10, 'lotus_hospital', 'Lotus Desk', 'hospital', 2, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(11, 'green_hospital', 'Green Valley Desk', 'hospital', 3, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(15, 'sunrise_hospital', 'Sunrise Desk', 'hospital', 4, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(12, 'officer_meera', 'Meera Shah', 'claims_officer', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(13, 'officer_rahul', 'Rahul Sen', 'claims_officer', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW()),
(14, 'admin_demo', 'Demo Administrator', 'admin', NULL, 'scrypt:32768:8:1$HTzQFqeD1dipjrox$69e0bc7f1afc2067c1a1060a1ef02835529e6e30f4dab0d797cd059374e2eefdfb548dcfa0586fb311cc6aeaa05165d35828450967cc652b1f92eb9816926717', NOW());

-- 4. POLICIES
INSERT INTO `policies` (`policy_id`, `holder_user_id`, `plan_id`, `start_date`, `end_date`, `status`) VALUES
(101, 1, 1, '2026-01-01', '2026-12-31', 'active'),
(102, 2, 2, '2026-04-01', '2027-03-31', 'active'),
(103, 3, 3, '2026-01-01', '2026-12-31', 'active'),
(104, 4, 1, '2025-01-01', '2025-12-31', 'expired'),
(105, 5, 2, '2026-01-01', '2026-12-31', 'active'),
(106, 6, 3, '2026-01-01', '2026-12-31', 'active'),
(107, 7, 1, '2026-01-01', '2026-12-31', 'active'),
(108, 8, 2, '2026-01-01', '2026-12-31', 'active');

-- 5. MEMBERS
INSERT INTO `members` (`member_id`, `policy_id`, `display_name`, `relationship`) VALUES
(201, 101, 'Aasha Rao', 'self'),
(202, 101, 'Nikhil Rao', 'spouse'),
(203, 102, 'Bilal Khan', 'self'),
(204, 103, 'Chitra Devi', 'self'),
(205, 103, 'Kiran Devi', 'child'),
(206, 104, 'Dev Kumar', 'self'),
(207, 105, 'Esha Reddy', 'self'),
(208, 106, 'Farhan Ali', 'self'),
(209, 106, 'Sara Ali', 'spouse'),
(210, 107, 'Gita Naik', 'self'),
(211, 108, 'Harish Babu', 'self');

-- 6. CLAIMS
INSERT INTO `claims` (`claim_id`, `policy_id`, `member_id`, `hospital_id`, `claim_type`, `treatment_type`, `admission_date`, `discharge_date`, `requested_amount_inr`, `status`, `eligible_amount_inr`, `officer_user_id`, `payment_recorded_date`) VALUES
(1001, 101, 201, 1, 'cashless', 'inpatient', '2026-08-10', '2026-08-13', 28000.00, 'paid', 26000.00, 12, '2026-08-14'),
(1002, 101, 202, 3, 'reimbursement', 'daycare', '2026-09-12', '2026-09-12', 14000.00, 'rejected', 0.00, 12, NULL),
(1003, 102, 203, 2, 'cashless', 'daycare', '2026-09-20', '2026-09-20', 18000.00, 'approved', 16000.00, 13, NULL),
(1004, 103, 204, 4, 'cashless', 'inpatient', '2026-10-02', '2026-10-05', 42000.00, 'in_review', NULL, 12, NULL),
(1005, 103, 205, 5, 'reimbursement', 'inpatient', '2026-10-03', '2026-10-06', 35000.00, 'more_info', NULL, 13, NULL),
(1006, 104, 206, 1, 'reimbursement', 'inpatient', '2026-07-01', '2026-07-03', 22000.00, 'rejected', 0.00, 12, NULL),
(1007, 105, 207, 1, 'cashless', 'inpatient', '2026-10-10', '2026-10-14', 85000.00, 'submitted', NULL, NULL, NULL),
(1008, 106, 208, 2, 'cashless', 'inpatient', '2026-09-01', '2026-09-05', 40000.00, 'paid', 38000.00, 13, '2026-09-08'),
(1009, 106, 209, 3, 'reimbursement', 'daycare', '2026-09-18', '2026-09-18', 12000.00, 'approved', 10000.00, 12, NULL),
(1010, 107, 210, 4, 'cashless', 'inpatient', '2026-10-15', '2026-10-18', 27000.00, 'draft', NULL, NULL, NULL),
(1011, 108, 211, 5, 'reimbursement', 'inpatient', '2026-09-25', '2026-09-27', 60000.00, 'more_info', NULL, 12, NULL),
(1012, 108, 211, 5, 'reimbursement', 'inpatient', '2026-09-25', '2026-09-27', 60000.00, 'submitted', NULL, NULL, NULL),
(1013, 102, 203, 1, 'cashless', 'inpatient', '2026-10-20', '2026-10-22', 45000.00, 'draft', NULL, NULL, NULL);

-- 7. CLAIM DOCUMENTS
INSERT INTO `claim_documents` (`claim_id`, `document_type`, `checklist_status`) VALUES
(1001, 'hospital_bill', 'received'),
(1001, 'discharge_summary', 'received'),
(1003, 'hospital_bill', 'received'),
(1003, 'discharge_summary', 'received'),
(1004, 'hospital_bill', 'received'),
(1004, 'discharge_summary', 'received'),
(1005, 'hospital_bill', 'received'),
(1005, 'discharge_summary', 'missing'),
(1006, 'hospital_bill', 'received'),
(1007, 'hospital_bill', 'received'),
(1008, 'hospital_bill', 'received'),
(1008, 'discharge_summary', 'received'),
(1009, 'hospital_bill', 'received'),
(1009, 'discharge_summary', 'received'),
(1011, 'hospital_bill', 'received'),
(1011, 'discharge_summary', 'missing'),
(1012, 'hospital_bill', 'received'),
(1012, 'discharge_summary', 'missing');

-- 8. CLAIM HISTORY
INSERT INTO `claim_history` (`claim_id`, `sequence_no`, `from_status`, `to_status`, `actor_user_id`, `note`, `event_date`) VALUES
(1001, 1, 'draft', 'submitted', 9, 'Synthetic submitted event', '2026-08-11'),
(1001, 2, 'submitted', 'in_review', 12, 'Synthetic in_review event', '2026-08-12'),
(1001, 3, 'in_review', 'approved', 12, 'Synthetic approved event', '2026-08-13'),
(1001, 4, 'approved', 'paid', 14, 'Synthetic paid event', '2026-08-14'),
(1002, 1, 'draft', 'submitted', 1, 'Synthetic submitted event', '2026-09-10'),
(1002, 2, 'submitted', 'in_review', 12, 'Synthetic in_review event', '2026-09-11'),
(1002, 3, 'in_review', 'rejected', 12, 'Synthetic rejected event', '2026-09-12'),
(1003, 1, 'draft', 'submitted', 10, 'Synthetic submitted event', '2026-09-18'),
(1003, 2, 'submitted', 'in_review', 13, 'Synthetic in_review event', '2026-09-19'),
(1003, 3, 'in_review', 'approved', 13, 'Synthetic approved event', '2026-09-20'),
(1004, 1, 'draft', 'submitted', 15, 'Synthetic submitted event', '2026-10-04'),
(1004, 2, 'submitted', 'in_review', 12, 'Synthetic in_review event', '2026-10-05'),
(1005, 1, 'draft', 'submitted', 3, 'Synthetic submitted event', '2026-10-04'),
(1005, 2, 'submitted', 'in_review', 13, 'Synthetic in_review event', '2026-10-05'),
(1005, 3, 'in_review', 'more_info', 13, 'Synthetic more_info event', '2026-10-06'),
(1006, 1, 'draft', 'submitted', 4, 'Synthetic submitted event', '2026-07-01'),
(1006, 2, 'submitted', 'in_review', 12, 'Synthetic in_review event', '2026-07-02'),
(1006, 3, 'in_review', 'rejected', 12, 'Synthetic rejected event', '2026-07-03'),
(1007, 1, 'draft', 'submitted', 9, 'Synthetic submitted event', '2026-10-14'),
(1008, 1, 'draft', 'submitted', 10, 'Synthetic submitted event', '2026-09-05'),
(1008, 2, 'submitted', 'in_review', 13, 'Synthetic in_review event', '2026-09-06'),
(1008, 3, 'in_review', 'approved', 13, 'Synthetic approved event', '2026-09-07'),
(1008, 4, 'approved', 'paid', 14, 'Synthetic paid event', '2026-09-08'),
(1009, 1, 'draft', 'submitted', 6, 'Synthetic submitted event', '2026-09-16'),
(1009, 2, 'submitted', 'in_review', 12, 'Synthetic in_review event', '2026-09-17'),
(1009, 3, 'in_review', 'approved', 12, 'Synthetic approved event', '2026-09-18'),
(1010, 1, NULL, 'draft', 15, 'Draft created', '2026-10-16'),
(1011, 1, 'draft', 'submitted', 8, 'Synthetic submitted event', '2026-09-25'),
(1011, 2, 'submitted', 'in_review', 12, 'Synthetic in_review event', '2026-09-26'),
(1011, 3, 'in_review', 'more_info', 12, 'Synthetic more_info event', '2026-09-27'),
(1012, 1, 'draft', 'submitted', 8, 'Synthetic submitted event', '2026-09-27'),
(1013, 1, NULL, 'draft', 9, 'Draft created', '2026-10-16');

-- 9. SETTLEMENTS
INSERT INTO `settlements` (`claim_id`, `payee_type`, `amount_inr`, `recorded_by_user_id`, `recorded_date`) VALUES
(1001, 'hospital', 21600.00, 14, '2026-08-14'),
(1008, 'hospital', 32850.00, 14, '2026-09-08');
