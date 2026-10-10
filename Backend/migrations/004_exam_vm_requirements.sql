ALTER TABLE exams
    ADD COLUMN slug VARCHAR(100) NULL,
    ADD UNIQUE KEY uq_exams_slug (slug);

ALTER TABLE attempts
    ADD COLUMN ssh_private_key_encrypted MEDIUMTEXT NULL,
    ADD COLUMN ssh_public_key TEXT NULL;

CREATE TABLE exam_vm_requirements (
    id INT NOT NULL AUTO_INCREMENT,
    exam_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    template_vmid INT NOT NULL,
    snap_id VARCHAR(255) NULL,
    node VARCHAR(100) NULL,
    ssh_username VARCHAR(100) NULL,
    is_main BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (id),
    KEY ix_exam_vm_requirements_exam_id (exam_id),
    CONSTRAINT fk_exam_vm_requirements_exam
        FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
);

CREATE TABLE attempt_vm_instances (
    id INT NOT NULL AUTO_INCREMENT,
    attempt_id INT NOT NULL,
    requirement_id INT NULL,
    name VARCHAR(100) NOT NULL,
    template_vmid INT NOT NULL,
    snap_id VARCHAR(255) NULL,
    vm_id INT NULL,
    node VARCHAR(100) NULL,
    task_upid VARCHAR(255) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'creating',
    ip_address VARCHAR(45) NULL,
    is_main BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    destroyed_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_attempt_vm_instances_vm_id (vm_id),
    KEY ix_attempt_vm_instances_attempt_id (attempt_id),
    KEY ix_attempt_vm_instances_requirement_id (requirement_id),
    CONSTRAINT fk_attempt_vm_instances_attempt
        FOREIGN KEY (attempt_id) REFERENCES attempts (id) ON DELETE CASCADE,
    CONSTRAINT fk_attempt_vm_instances_requirement
        FOREIGN KEY (requirement_id) REFERENCES exam_vm_requirements (id) ON DELETE SET NULL
);
