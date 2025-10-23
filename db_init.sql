-- Backend schema for the IIS + Python HealthCheck app

-- USERS & ROLES
CREATE TABLE users (
  user_id        NUMBER PRIMARY KEY,
  login_id       VARCHAR2(64) UNIQUE NOT NULL,
  full_name      VARCHAR2(128) NOT NULL,
  email          VARCHAR2(256) NOT NULL,
  role           VARCHAR2(16) CHECK (role IN ('ADMIN','SUPER','USER')) NOT NULL,
  password_hash  VARCHAR2(255) NOT NULL,
  active         NUMBER(1) DEFAULT 1 NOT NULL,
  created_at     DATE DEFAULT SYSDATE,
  updated_at     DATE
);
CREATE SEQUENCE users_seq;

-- ORACLE MODULE TABLES
CREATE TABLE oracle_targets (
  target_id            NUMBER PRIMARY KEY,
  s_no                 NUMBER,
  db_name              VARCHAR2(128) NOT NULL,
  environment          VARCHAR2(64) NOT NULL,
  host                 VARCHAR2(256),
  db_version           VARCHAR2(64),
  method               VARCHAR2(8) CHECK (method IN ('THIN','TNS')) NOT NULL,
  tns_alias            VARCHAR2(128),
  host_name            VARCHAR2(256),
  port                 NUMBER,
  service_name         VARCHAR2(256),
  common_user          VARCHAR2(128) NOT NULL,
  common_password_enc  CLOB,
  status               VARCHAR2(32),
  instance_status      VARCHAR2(64),
  db_open_mode         VARCHAR2(64),
  worst_tbs_pct        NUMBER(6,2),
  tablespaces_online   NUMBER(1),
  last_full_backup     DATE,
  last_arch_backup     DATE,
  last_check           DATE,
  check_status         VARCHAR2(32),
  error_msg            CLOB,
  is_active            NUMBER(1) DEFAULT 1
);
CREATE SEQUENCE oracle_targets_seq;

CREATE TABLE oracle_checks (
  check_id           NUMBER PRIMARY KEY,
  target_id          NUMBER REFERENCES oracle_targets(target_id),
  instance_status    VARCHAR2(64),
  db_open_mode       VARCHAR2(64),
  worst_tbs_pct      NUMBER(6,2),
  tablespaces_online NUMBER(1),
  last_full_backup   DATE,
  last_arch_backup   DATE,
  started_at         DATE,
  completed_at       DATE,
  status             VARCHAR2(32),
  error_msg          CLOB
);
CREATE SEQUENCE oracle_checks_seq;

-- SQL SERVER MODULE TABLES
CREATE TABLE sqlserver_targets (
  target_id      NUMBER PRIMARY KEY,
  s_no           NUMBER,
  instance_name  VARCHAR2(256) NOT NULL,
  environment    VARCHAR2(64) NOT NULL,
  host           VARCHAR2(256),
  version        VARCHAR2(64),
  auth_mode      VARCHAR2(16) CHECK (auth_mode IN ('SQL','WINDOWS')) NOT NULL,
  username       VARCHAR2(128),
  password_enc   CLOB,
  domain         VARCHAR2(128),
  status         VARCHAR2(32),
  last_check     DATE,
  check_status   VARCHAR2(32),
  error_msg      CLOB,
  is_active      NUMBER(1) DEFAULT 1
);
CREATE SEQUENCE sqlserver_targets_seq;

CREATE TABLE sqlserver_checks (
  check_id      NUMBER PRIMARY KEY,
  target_id     NUMBER REFERENCES sqlserver_targets(target_id),
  status_text   CLOB,
  started_at    DATE,
  completed_at  DATE,
  status        VARCHAR2(32),
  error_msg     CLOB
);
CREATE SEQUENCE sqlserver_checks_seq;

-- Indexes (optional)
CREATE INDEX idx_users_login ON users(login_id);
CREATE INDEX idx_oratgt_name ON oracle_targets(db_name);
CREATE INDEX idx_sqltgt_inst ON sqlserver_targets(instance_name);
