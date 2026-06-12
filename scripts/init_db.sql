-- ============================================================
-- ChaoXingAgent 数据库初始化脚本
-- 数据库: MySQL 8.0+
-- 字符集: utf8mb4 / utf8mb4_unicode_ci
-- 引擎:   InnoDB
--
-- 用法:
--   mysql -u root -p --default-character-set=utf8mb4 < scripts/init_db.sql
-- ============================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 建库
CREATE DATABASE IF NOT EXISTS `chaoxing`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `chaoxing`;

-- ============================================================
-- 1. users — 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
  `id`                 INT           NOT NULL AUTO_INCREMENT,
  `user_id`            VARCHAR(64)   NOT NULL COMMENT '系统内部用户ID',
  `platform_user_id`   VARCHAR(128)  DEFAULT NULL COMMENT '外部平台用户ID',
  `platform_id`        VARCHAR(64)   DEFAULT NULL COMMENT '外部平台标识',
  `user_name`          VARCHAR(128)  NOT NULL DEFAULT '' COMMENT '用户姓名',
  `role`               VARCHAR(16)   NOT NULL DEFAULT 'student' COMMENT '角色: student/teacher',
  `school_id`          VARCHAR(64)   DEFAULT NULL COMMENT '学校ID',
  `email`              VARCHAR(256)  DEFAULT NULL COMMENT '邮箱',
  `phone`              VARCHAR(32)   DEFAULT NULL COMMENT '手机号',
  `auth_token`         TEXT          DEFAULT NULL COMMENT '身份验证令牌',
  `related_course_ids` TEXT          DEFAULT NULL COMMENT '关联课程ID列表(JSON)',
  `created_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================================
-- 2. courses — 课程表
-- ============================================================
CREATE TABLE IF NOT EXISTS `courses` (
  `id`                  INT           NOT NULL AUTO_INCREMENT,
  `course_id`           VARCHAR(64)   NOT NULL COMMENT '系统内部课程ID',
  `platform_course_id`  VARCHAR(128)  DEFAULT NULL COMMENT '外部平台课程ID',
  `platform_id`         VARCHAR(64)   DEFAULT NULL COMMENT '外部平台标识',
  `course_name`         VARCHAR(256)  NOT NULL DEFAULT '' COMMENT '课程名称',
  `school_id`           VARCHAR(64)   DEFAULT NULL COMMENT '学校ID',
  `school_name`         VARCHAR(256)  DEFAULT NULL COMMENT '学校名称',
  `teacher_info`        TEXT          DEFAULT NULL COMMENT '教师信息(JSON)',
  `term`                VARCHAR(32)   DEFAULT NULL COMMENT '学期',
  `credit`              FLOAT         DEFAULT NULL COMMENT '学分',
  `period`              INT           DEFAULT NULL COMMENT '学时',
  `course_cover`        VARCHAR(512)  DEFAULT NULL COMMENT '课程封面URL',
  `created_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_course_id` (`course_id`),
  KEY `idx_course_id` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程表';

-- ============================================================
-- 3. parse_tasks — 解析任务表
-- ============================================================
CREATE TABLE IF NOT EXISTS `parse_tasks` (
  `id`                   INT           NOT NULL AUTO_INCREMENT,
  `parse_id`             VARCHAR(64)   NOT NULL COMMENT '解析任务ID',
  `school_id`            VARCHAR(64)   DEFAULT NULL COMMENT '学校ID',
  `user_id`              VARCHAR(64)   DEFAULT NULL COMMENT '发起用户ID',
  `course_id`            VARCHAR(64)   DEFAULT NULL COMMENT '课程ID',
  `file_type`            VARCHAR(16)   NOT NULL COMMENT '文件类型',
  `file_url`             VARCHAR(1024) NOT NULL COMMENT '文件URL/路径',
  `file_name`            VARCHAR(512)  NOT NULL DEFAULT '' COMMENT '文件名',
  `file_size`            INT           DEFAULT NULL COMMENT '文件大小(字节)',
  `page_count`           INT           DEFAULT NULL COMMENT '页数',
  `is_extract_key_point` TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否提取重点',
  `task_status`          VARCHAR(16)   NOT NULL DEFAULT 'processing' COMMENT '状态: processing/completed/failed',
  `structure_preview`    LONGTEXT      DEFAULT NULL COMMENT '知识点结构预览(JSON)',
  `parser_output`        LONGTEXT      DEFAULT NULL COMMENT '完整解析输出(JSON)',
  `error_message`        TEXT          DEFAULT NULL COMMENT '错误信息',
  `created_at`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_parse_id` (`parse_id`),
  KEY `idx_parse_user` (`user_id`),
  KEY `idx_parse_course` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='解析任务表';

-- ============================================================
-- 4. scripts — 脚本表
-- ============================================================
CREATE TABLE IF NOT EXISTS `scripts` (
  `id`               INT           NOT NULL AUTO_INCREMENT,
  `script_id`        VARCHAR(64)   NOT NULL COMMENT '脚本ID',
  `parse_id`         VARCHAR(64)   NOT NULL COMMENT '关联解析任务ID',
  `lesson_id`        VARCHAR(64)   DEFAULT NULL COMMENT '关联智课ID',
  `teaching_style`   VARCHAR(32)   NOT NULL DEFAULT 'standard' COMMENT '讲授风格',
  `speech_speed`     VARCHAR(16)   NOT NULL DEFAULT 'normal' COMMENT '语速',
  `custom_opening`   TEXT          DEFAULT NULL COMMENT '自定义开场白',
  `script_structure` LONGTEXT      DEFAULT NULL COMMENT '脚本结构(JSON)',
  `generate_output`  LONGTEXT      DEFAULT NULL COMMENT '完整生成输出(JSON)',
  `task_status`      VARCHAR(16)   NOT NULL DEFAULT 'processing' COMMENT '状态: processing/completed/failed',
  `error_message`    TEXT          DEFAULT NULL COMMENT '错误信息',
  `created_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_script_id` (`script_id`),
  KEY `idx_script_parse` (`parse_id`),
  KEY `idx_script_lesson` (`lesson_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='脚本表';

-- ============================================================
-- 5. audio_tasks — 音频任务表
-- ============================================================
CREATE TABLE IF NOT EXISTS `audio_tasks` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `audio_id`        VARCHAR(64)   NOT NULL COMMENT '音频任务ID',
  `script_id`       VARCHAR(64)   NOT NULL COMMENT '关联脚本ID',
  `voice_type`      VARCHAR(32)   NOT NULL DEFAULT 'female_standard' COMMENT '语音类型',
  `audio_format`    VARCHAR(8)    NOT NULL DEFAULT 'mp3' COMMENT '音频格式',
  `section_ids`     TEXT          DEFAULT NULL COMMENT '指定章节ID(JSON)',
  `audio_url`       VARCHAR(1024) DEFAULT NULL COMMENT '音频文件URL',
  `total_duration`  INT           DEFAULT NULL COMMENT '总时长(秒)',
  `file_size`       INT           DEFAULT NULL COMMENT '文件大小(字节)',
  `bit_rate`        INT           DEFAULT NULL COMMENT '比特率',
  `section_audios`  LONGTEXT      DEFAULT NULL COMMENT '分章节音频信息(JSON)',
  `task_status`     VARCHAR(16)   NOT NULL DEFAULT 'processing' COMMENT '状态: processing/completed/failed',
  `error_message`   TEXT          DEFAULT NULL COMMENT '错误信息',
  `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_audio_id` (`audio_id`),
  KEY `idx_audio_script` (`script_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='音频任务表';

-- ============================================================
-- 6. lessons — 智课表
-- ============================================================
CREATE TABLE IF NOT EXISTS `lessons` (
  `id`                  INT           NOT NULL AUTO_INCREMENT,
  `lesson_id`           VARCHAR(64)   NOT NULL COMMENT '智课ID',
  `course_id`           VARCHAR(64)   DEFAULT NULL COMMENT '课程ID',
  `parse_id`            VARCHAR(64)   DEFAULT NULL COMMENT '关联解析任务ID',
  `script_id`           VARCHAR(64)   DEFAULT NULL COMMENT '关联脚本ID',
  `knowledge_base_id`   VARCHAR(64)   DEFAULT NULL COMMENT '关联知识库ID',
  `lesson_name`         VARCHAR(256)  NOT NULL DEFAULT '' COMMENT '智课名称',
  `status`              VARCHAR(16)   NOT NULL DEFAULT 'draft' COMMENT '状态: draft/published/archived',
  `structured_content`  LONGTEXT      DEFAULT NULL COMMENT '结构化教学内容(JSON)',
  `content_hash`        VARCHAR(64)   DEFAULT NULL COMMENT '结构化内容版本哈希',
  `ppt_outline`         LONGTEXT      DEFAULT NULL COMMENT 'PPT大纲(JSON)',
  `rendered_ppt_path`   VARCHAR(1024) DEFAULT NULL COMMENT '渲染后PPTX路径',
  `created_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_lesson_id` (`lesson_id`),
  KEY `idx_lesson_course` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='智课表';

-- ============================================================
-- 7. qa_sessions — 问答会话表
-- ============================================================
CREATE TABLE IF NOT EXISTS `qa_sessions` (
  `id`                       INT         NOT NULL AUTO_INCREMENT,
  `session_id`               VARCHAR(64) NOT NULL COMMENT '会话ID',
  `user_id`                  VARCHAR(64) NOT NULL COMMENT '学生用户ID',
  `school_id`                VARCHAR(64) DEFAULT NULL COMMENT '学校ID',
  `course_id`                VARCHAR(64) NOT NULL COMMENT '课程ID',
  `lesson_id`                VARCHAR(64) NOT NULL COMMENT '智课ID',
  `status`                   VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态: active/paused/completed',
  `current_section_id`       VARCHAR(64) DEFAULT NULL COMMENT '当前章节ID',
  `current_page`             INT         DEFAULT NULL COMMENT '当前页码',
  `current_script_block_id`  VARCHAR(64) DEFAULT NULL COMMENT '当前讲稿块ID',
  `progress_percent`         FLOAT       NOT NULL DEFAULT 0 COMMENT '会话进度百分比',
  `last_action`              VARCHAR(32) DEFAULT NULL COMMENT '最近一次教学动作',
  `created_at`               DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`               DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_session_id` (`session_id`),
  KEY `idx_session_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答会话表';

-- ============================================================
-- 8. qa_records — 问答记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS `qa_records` (
  `id`                       INT          NOT NULL AUTO_INCREMENT,
  `answer_id`                VARCHAR(64)  NOT NULL COMMENT '回答ID',
  `session_id`               VARCHAR(64)  NOT NULL COMMENT '所属会话ID',
  `user_id`                  VARCHAR(64)  NOT NULL COMMENT '学生用户ID',
  `course_id`                VARCHAR(64)  NOT NULL COMMENT '课程ID',
  `lesson_id`                VARCHAR(64)  NOT NULL COMMENT '智课ID',
  `question_type`            VARCHAR(8)   NOT NULL DEFAULT 'text' COMMENT '提问类型: text/voice',
  `student_question_type`    VARCHAR(32)  DEFAULT NULL COMMENT '学生问题语义分类',
  `question_content`         TEXT         NOT NULL COMMENT '提问内容',
  `current_section_id`       VARCHAR(64)  DEFAULT NULL COMMENT '提问时所在章节ID',
  `current_page`             INT          DEFAULT NULL COMMENT '提问时所在页码',
  `current_script_block_id`  VARCHAR(64)  DEFAULT NULL COMMENT '提问时所在讲稿块ID',
  `answer_content`           TEXT         DEFAULT NULL COMMENT '系统回答',
  `answer_type`              VARCHAR(16)  NOT NULL DEFAULT 'text' COMMENT '回答类型: text/mixed',
  `related_knowledge`        TEXT         DEFAULT NULL COMMENT '关联知识点(JSON)',
  `suggestions`              TEXT         DEFAULT NULL COMMENT '追问建议(JSON)',
  `references_json`          LONGTEXT     DEFAULT NULL COMMENT '检索引用(JSON)',
  `understanding_level`      VARCHAR(16)  DEFAULT NULL COMMENT '理解程度: full/partial/none',
  `next_action`              VARCHAR(32)  DEFAULT NULL COMMENT '下一步教学动作',
  `reason`                   TEXT         DEFAULT NULL COMMENT '动作原因',
  `matched_section_id`       VARCHAR(64)  DEFAULT NULL COMMENT '主命中章节ID',
  `matched_page`             INT          DEFAULT NULL COMMENT '主命中页码',
  `target_section_id`        VARCHAR(64)  DEFAULT NULL COMMENT '目标章节ID',
  `target_page`              INT          DEFAULT NULL COMMENT '目标页码',
  `created_at`               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_answer_id` (`answer_id`),
  KEY `idx_record_session` (`session_id`),
  KEY `idx_record_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答记录表';

-- ============================================================
-- 9. learning_progress — 学习进度表
-- ============================================================
CREATE TABLE IF NOT EXISTS `learning_progress` (
  `id`                   INT           NOT NULL AUTO_INCREMENT,
  `track_id`             VARCHAR(64)   NOT NULL COMMENT '追踪记录ID',
  `school_id`            VARCHAR(64)   DEFAULT NULL COMMENT '学校ID',
  `user_id`              VARCHAR(64)   NOT NULL COMMENT '学生用户ID',
  `course_id`            VARCHAR(64)   NOT NULL COMMENT '课程ID',
  `lesson_id`            VARCHAR(64)   NOT NULL COMMENT '智课ID',
  `current_section_id`   VARCHAR(64)   DEFAULT NULL COMMENT '当前章节ID',
  `progress_percent`     FLOAT         NOT NULL DEFAULT 0.0 COMMENT '章节学习进度(0-100)',
  `total_progress`       FLOAT         NOT NULL DEFAULT 0.0 COMMENT '智课总学习进度(0-100)',
  `next_section_suggest` VARCHAR(64)   DEFAULT NULL COMMENT '建议后续学习章节',
  `last_operate_time`    VARCHAR(32)   DEFAULT NULL COMMENT '最后操作时间',
  `qa_record_id`         VARCHAR(64)   DEFAULT NULL COMMENT '最近问答记录ID',
  `created_at`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_track_id` (`track_id`),
  KEY `idx_progress_user` (`user_id`),
  KEY `idx_progress_lesson` (`lesson_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学习进度表';

-- ============================================================
-- 10. adjust_records — 节奏调整记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS `adjust_records` (
  `id`                  INT         NOT NULL AUTO_INCREMENT,
  `adjust_id`           VARCHAR(64) NOT NULL COMMENT '调整记录ID',
  `user_id`             VARCHAR(64) NOT NULL COMMENT '学生用户ID',
  `lesson_id`           VARCHAR(64) NOT NULL COMMENT '智课ID',
  `current_section_id`  VARCHAR(64) NOT NULL COMMENT '当前章节ID',
  `understanding_level` VARCHAR(16) NOT NULL COMMENT '理解程度',
  `qa_record_id`        VARCHAR(64) DEFAULT NULL COMMENT '关联问答记录ID',
  `adjust_type`         VARCHAR(32) NOT NULL COMMENT '调整类型: normal/supplement',
  `continue_section_id` VARCHAR(64) DEFAULT NULL COMMENT '续讲章节ID',
  `supplement_content`  TEXT        DEFAULT NULL COMMENT '补充内容(JSON)',
  `next_sections`       TEXT        DEFAULT NULL COMMENT '后续章节调整方案(JSON)',
  `created_at`          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_adjust_id` (`adjust_id`),
  KEY `idx_adjust_user` (`user_id`),
  KEY `idx_adjust_lesson` (`lesson_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='节奏调整记录表';


-- ============================================================
-- 11. knowledge_bases — 知识库表
-- ============================================================
CREATE TABLE IF NOT EXISTS `knowledge_bases` (
  `id`               INT           NOT NULL AUTO_INCREMENT,
  `kb_id`            VARCHAR(64)   NOT NULL COMMENT '知识库ID',
  `course_id`        VARCHAR(64)   DEFAULT NULL COMMENT '课程ID',
  `kb_name`          VARCHAR(256)  NOT NULL DEFAULT '' COMMENT '知识库名称',
  `scope_type`       VARCHAR(16)   NOT NULL DEFAULT 'course' COMMENT '范围: lesson/course/custom',
  `status`           VARCHAR(16)   NOT NULL DEFAULT 'draft' COMMENT '状态: draft/indexing/ready/failed',
  `index_backend`    VARCHAR(16)   NOT NULL DEFAULT 'faiss' COMMENT '索引后端: faiss/qdrant',
  `embedding_model`  VARCHAR(64)   DEFAULT NULL COMMENT 'Embedding模型标识',
  `index_path`       VARCHAR(1024) DEFAULT NULL COMMENT '索引文件路径',
  `chunk_count`      INT           NOT NULL DEFAULT 0 COMMENT 'Chunk总数',
  `source_count`     INT           NOT NULL DEFAULT 0 COMMENT '来源文档总数',
  `created_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_kb_id` (`kb_id`),
  KEY `idx_kb_course` (`course_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

-- ============================================================
-- 12. knowledge_base_sources — 知识库来源表
-- ============================================================
CREATE TABLE IF NOT EXISTS `knowledge_base_sources` (
  `id`            INT           NOT NULL AUTO_INCREMENT,
  `kb_source_id`  VARCHAR(64)   NOT NULL COMMENT '来源记录ID',
  `kb_id`         VARCHAR(64)   NOT NULL COMMENT '知识库ID',
  `source_kind`   VARCHAR(16)   NOT NULL COMMENT '来源类型: lesson/parse_task/file',
  `lesson_id`     VARCHAR(64)   DEFAULT NULL COMMENT '关联智课ID',
  `parse_id`      VARCHAR(64)   DEFAULT NULL COMMENT '关联解析任务ID',
  `file_url`      VARCHAR(1024) DEFAULT NULL COMMENT '文件URL',
  `file_name`     VARCHAR(512)  DEFAULT NULL COMMENT '文件名',
  `source_hash`   VARCHAR(64)   DEFAULT NULL COMMENT '来源内容哈希',
  `status`        VARCHAR(16)   NOT NULL DEFAULT 'pending' COMMENT '状态: pending/indexed/failed',
  `created_at`    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_kb_source_id` (`kb_source_id`),
  KEY `idx_kbs_kb` (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库来源表';

-- ============================================================
-- 13. knowledge_chunks — 知识库Chunk元数据表
-- ============================================================
CREATE TABLE IF NOT EXISTS `knowledge_chunks` (
  `id`              INT           NOT NULL AUTO_INCREMENT,
  `chunk_id`        VARCHAR(64)   NOT NULL COMMENT 'Chunk ID',
  `kb_id`           VARCHAR(64)   NOT NULL COMMENT '知识库ID',
  `lesson_id`       VARCHAR(64)   DEFAULT NULL COMMENT '关联智课ID',
  `source_type`     VARCHAR(32)   NOT NULL COMMENT '来源类型: page/section/script_block',
  `source_id`       VARCHAR(128)  NOT NULL COMMENT '来源对象ID',
  `section_id`      VARCHAR(64)   DEFAULT NULL COMMENT '章节ID',
  `page`            INT           DEFAULT NULL COMMENT '页码',
  `title`           VARCHAR(512)  DEFAULT NULL COMMENT '标题',
  `text`            LONGTEXT      NOT NULL COMMENT 'Chunk文本',
  `chunk_index`     INT           NOT NULL DEFAULT 0 COMMENT 'Chunk序号',
  `key_points_json` TEXT          DEFAULT NULL COMMENT '关键知识点(JSON)',
  `metadata_json`   TEXT          DEFAULT NULL COMMENT '附加元数据(JSON)',
  `created_at`      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_chunk_id` (`chunk_id`),
  KEY `idx_kc_kb` (`kb_id`),
  KEY `idx_kc_lesson` (`lesson_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库Chunk元数据表';


-- ============================================================
-- 插入示例数据
-- ============================================================

-- 1. 示例教师用户
INSERT INTO `users` (`user_id`, `platform_user_id`, `platform_id`, `user_name`, `role`, `school_id`, `email`, `phone`, `auth_token`, `related_course_ids`)
VALUES ('tea20001', 'plat_tea001', 'plat001', '张教授', 'teacher', 'sch10001', 'zhangjs@example.edu.cn', '13800000001', 'eyJhbGciOiJIUzI1NiJ9.dGVhMjAwMDE.demo_token', '["cou30001"]');

-- 2. 示例学生用户
INSERT INTO `users` (`user_id`, `platform_user_id`, `platform_id`, `user_name`, `role`, `school_id`, `email`, `phone`, `auth_token`, `related_course_ids`)
VALUES ('stu20001', 'plat_stu001', 'plat001', '李四', 'student', 'sch10001', 'lisi@example.edu.cn', '13800000002', 'eyJhbGciOiJIUzI1NiJ9.c3R1MjAwMDE.demo_token', '["cou30001"]');

-- 3. 示例课程
INSERT INTO `courses` (`course_id`, `platform_course_id`, `platform_id`, `course_name`, `school_id`, `school_name`, `teacher_info`, `term`, `credit`, `period`, `course_cover`)
VALUES ('cou30001', 'plat_cou001', 'plat001', '材料力学（上册）', 'sch10001', '某某大学',
        '[{"teacherId":"plat_tea001","teacherName":"张教授"}]',
        '20242', 3.0, 48, 'http://example.com/course/cover/001.jpg');

-- 4. 示例解析任务
INSERT INTO `parse_tasks` (`parse_id`, `school_id`, `user_id`, `course_id`, `file_type`, `file_url`, `file_name`, `file_size`, `page_count`, `is_extract_key_point`, `task_status`, `structure_preview`)
VALUES ('parse20240520001', 'sch10001', 'tea20001', 'cou30001', 'pptx',
        'http://example.com/course/ppt/材料力学-梁弯曲理论.pptx',
        '材料力学-梁弯曲理论.pptx', 2048000, 25, 1, 'completed',
        '{"chapters":[{"chapterId":"chap001","chapterName":"梁弯曲理论基础","subChapters":[{"subChapterId":"sub001","subChapterName":"平面假设的定义","isKeyPoint":true,"pageRange":"3-5"}]}]}');

-- 5. 示例脚本
INSERT INTO `scripts` (`script_id`, `parse_id`, `lesson_id`, `teaching_style`, `speech_speed`, `custom_opening`, `task_status`, `script_structure`)
VALUES ('script20240520001', 'parse20240520001', 'lesson20240520001', 'standard', 'normal',
        '同学们好，今天我们学习梁弯曲理论的核心知识点', 'completed',
        '[{"sectionId":"sec001","sectionName":"开场白","content":"同学们好，今天我们将深入学习材料力学中的梁弯曲理论，这部分内容是后续工程结构设计的重要基础。","duration":15,"keyPoints":[]},{"sectionId":"sec002","sectionName":"平面假设的定义","content":"平面假设是梁弯曲理论的基本假设，指梁变形前垂直于轴线的平面截面，变形后仍保持为平面且垂直于变形后的轴线。","duration":45,"keyPoints":["平面假设的核心内涵","变形前后截面特性","假设的工程意义"]}]');

-- 6. 示例音频任务
INSERT INTO `audio_tasks` (`audio_id`, `script_id`, `voice_type`, `audio_format`, `section_ids`, `audio_url`, `total_duration`, `file_size`, `bit_rate`, `task_status`, `section_audios`)
VALUES ('audio20240520001', 'script20240520001', 'female_standard', 'mp3',
        '["sec001","sec002"]',
        '/data/audio/audio20240520001.mp3', 600, 9600000, 128000, 'completed',
        '[{"sectionId":"sec001","audioUrl":"/data/audio/section/sec001.mp3","duration":15},{"sectionId":"sec002","audioUrl":"/data/audio/section/sec002.mp3","duration":45}]');

-- 7. 示例智课
INSERT INTO `lessons` (`lesson_id`, `course_id`, `parse_id`, `script_id`, `lesson_name`, `status`, `structured_content`, `ppt_outline`)
VALUES ('lesson20240520001', 'cou30001', 'parse20240520001', 'script20240520001',
        '材料力学-梁弯曲理论', 'published',
        '{"course_id":"cou30001","lesson_id":"lesson20240520001","lesson_summary":"本节讲解梁弯曲理论的基本假设与正应力公式推导","pages":[{"page":1,"page_id":"page_1","title":"平面假设的定义","content":"平面假设是梁弯曲理论的基本假设...","summary":"平面假设定义与意义","key_points":["平面假设核心内涵"],"knowledge_points":["平面假设"],"section_id":"sec_1","page_role":"content","source_unit_ids":["unit_1"]}],"sections":[{"section_id":"sec_1","name":"梁弯曲理论基础","summary":"讲解平面假设及其工程意义","page_range":[1,2,3],"key_points":["平面假设","正应力分布"],"knowledge_points":["平面假设","弯曲正应力"],"source_unit_ids":["unit_1","unit_2"],"section_type":"content"},{"section_id":"sec_2","name":"正应力公式推导","summary":"推导弯曲正应力计算公式","page_range":[4,5],"key_points":["正应力公式","截面惯性矩"],"knowledge_points":["弯曲正应力公式","惯性矩"],"source_unit_ids":["unit_3","unit_4"],"section_type":"content"}],"knowledge_points":["平面假设","弯曲正应力","截面惯性矩"]}',
        '{"deck_title":"材料力学-梁弯曲理论","theme_name":"default_teaching","slides":[{"slide_id":"slide_1","slide_type":"cover","title":"材料力学-梁弯曲理论","bullets":[]},{"slide_id":"slide_2","slide_type":"concept","title":"平面假设的定义","bullets":["平面假设的核心内涵","变形前后截面特性","假设的工程意义"]}]}');

-- 8. 示例问答会话
INSERT INTO `qa_sessions` (`session_id`, `user_id`, `school_id`, `course_id`, `lesson_id`, `status`)
VALUES ('ses20240520001', 'stu20001', 'sch10001', 'cou30001', 'lesson20240520001', 'active');

-- 9. 示例问答记录
INSERT INTO `qa_records` (`answer_id`, `session_id`, `user_id`, `course_id`, `lesson_id`, `question_type`, `question_content`, `current_section_id`, `answer_content`, `answer_type`, `related_knowledge`, `suggestions`, `understanding_level`)
VALUES ('ans20240520001', 'ses20240520001', 'stu20001', 'cou30001', 'lesson20240520001',
        'text', '平面假设为什么能简化梁弯曲问题？', 'sec_1',
        '平面假设之所以能简化梁弯曲问题，核心原因是它忽略了剪切变形对截面形状的影响，使得梁弯曲时的正应力沿截面高度呈线性分布。这样就可以用几何关系直接推导正应力公式，无需考虑复杂的剪切变形影响。',
        'text',
        '{"knowledgeId":"know001","knowledgeName":"平面假设的工程简化意义","relatedSectionId":"sec_1"}',
        '["想了解平面假设的适用范围吗？","需要结合具体例题理解正应力分布吗？"]',
        'partial');

-- 10. 示例学习进度
INSERT INTO `learning_progress` (`track_id`, `school_id`, `user_id`, `course_id`, `lesson_id`, `current_section_id`, `progress_percent`, `total_progress`, `next_section_suggest`, `last_operate_time`, `qa_record_id`)
VALUES ('track20240520001', 'sch10001', 'stu20001', 'cou30001', 'lesson20240520001',
        'sec_1', 60.5, 45.2, 'sec_2', '2024-05-20 10:10:00', 'ans20240520001');

-- 11. 示例节奏调整记录
INSERT INTO `adjust_records` (`adjust_id`, `user_id`, `lesson_id`, `current_section_id`, `understanding_level`, `qa_record_id`, `adjust_type`, `continue_section_id`, `supplement_content`, `next_sections`)
VALUES ('adj20240520001', 'stu20001', 'lesson20240520001', 'sec_1', 'partial', 'ans20240520001',
        'supplement', 'sec_1',
        '{"content":"为了进一步理解平面假设的简化作用，我们以矩形截面梁为例...","duration":30,"relatedExample":"工程中常见的简支梁弯曲问题，均基于平面假设推导正应力公式"}',
        '[{"sectionId":"sec_1","adjustedDuration":75,"isKeyPointStrengthen":true},{"sectionId":"sec_2","adjustedDuration":40,"isKeyPointStrengthen":false}]');
