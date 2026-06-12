-- ============================================================
-- Migration: Student Agent Refactor
-- Date: 2026-04-02
-- Description:
--   - Extend qa_sessions with position/progress fields
--     (replaces agent-private SQLite SessionStore)
--   - Extend qa_records with full agent output fields
--   - Add knowledge_base_id + content_hash to lessons
-- ============================================================

USE `chaoxing`;

-- ─── 1. qa_sessions: add position & progress fields ────────

ALTER TABLE `qa_sessions`
  ADD COLUMN `current_section_id`      VARCHAR(64)  DEFAULT NULL COMMENT '当前章节ID' AFTER `status`,
  ADD COLUMN `current_page`            INT          DEFAULT NULL COMMENT '当前页码' AFTER `current_section_id`,
  ADD COLUMN `current_script_block_id` VARCHAR(64)  DEFAULT NULL COMMENT '当前讲稿块ID' AFTER `current_page`,
  ADD COLUMN `progress_percent`        FLOAT        NOT NULL DEFAULT 0 COMMENT '会话进度百分比' AFTER `current_script_block_id`,
  ADD COLUMN `last_action`             VARCHAR(32)  DEFAULT NULL COMMENT '最近一次教学动作' AFTER `progress_percent`;


-- ─── 2. qa_records: add full agent output fields ────────────

ALTER TABLE `qa_records`
  ADD COLUMN `current_page`            INT          DEFAULT NULL COMMENT '提问时所在页码' AFTER `current_section_id`,
  ADD COLUMN `current_script_block_id` VARCHAR(64)  DEFAULT NULL COMMENT '提问时所在讲稿块ID' AFTER `current_page`,
  ADD COLUMN `student_question_type`   VARCHAR(32)  DEFAULT NULL COMMENT '学生问题语义分类' AFTER `question_type`,
  ADD COLUMN `references_json`         LONGTEXT     DEFAULT NULL COMMENT '检索引用(JSON)' AFTER `suggestions`,
  ADD COLUMN `next_action`             VARCHAR(32)  DEFAULT NULL COMMENT '下一步教学动作' AFTER `understanding_level`,
  ADD COLUMN `reason`                  TEXT         DEFAULT NULL COMMENT '动作原因' AFTER `next_action`,
  ADD COLUMN `matched_section_id`      VARCHAR(64)  DEFAULT NULL COMMENT '主命中章节ID' AFTER `references_json`,
  ADD COLUMN `matched_page`            INT          DEFAULT NULL COMMENT '主命中页码' AFTER `matched_section_id`,
  ADD COLUMN `target_section_id`       VARCHAR(64)  DEFAULT NULL COMMENT '目标章节ID' AFTER `matched_page`,
  ADD COLUMN `target_page`             INT          DEFAULT NULL COMMENT '目标页码' AFTER `target_section_id`;


-- ─── 3. lessons: add knowledge_base link + content_hash ─────

ALTER TABLE `lessons`
  ADD COLUMN `knowledge_base_id` VARCHAR(64) DEFAULT NULL COMMENT '关联知识库ID' AFTER `script_id`,
  ADD COLUMN `content_hash`      VARCHAR(64) DEFAULT NULL COMMENT '结构化内容版本哈希' AFTER `structured_content`;
