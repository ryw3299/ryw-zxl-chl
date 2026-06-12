"""Pydantic response models for all API endpoints.

Provides structured response schemas for FastAPI's automatic
OpenAPI/Swagger documentation generation.
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应格式（遵循超星开放 API 设计规范）"""

    code: int = Field(200, description="状态码：200 成功，4xx 客户端错误，5xx 服务端错误", example=200)
    msg: str = Field("操作成功", description="状态描述", example="操作成功")
    data: Optional[T] = Field(None, description="业务数据（成功时返回，格式随接口变化）")
    requestId: str = Field("", description="请求唯一标识（用于问题排查）", example="req20240520001")


class ErrorResponse(BaseModel):
    """错误响应格式"""

    code: int = Field(400, description="错误状态码", example=400)
    msg: str = Field("参数错误", description="错误描述", example="参数错误")
    data: None = Field(None, description="错误时为 null")
    requestId: str = Field("", description="请求唯一标识", example="req20240520001")


# ── 智课生成模块 ─────────────────────────────────────────────────────


class FileInfo(BaseModel):
    fileName: str = Field("", description="文件名", example="材料力学-梁弯曲理论.pptx")
    fileSize: int = Field(0, description="文件大小（字节）", example=2048000)
    pageCount: int = Field(0, description="页数", example=25)


class SubChapter(BaseModel):
    subChapterId: str = Field("", description="子章节 ID", example="sub001")
    subChapterName: str = Field("", description="子章节名称", example="平面假设的定义")
    isKeyPoint: bool = Field(False, description="是否重点")
    pageRange: str = Field("", description="对应课件页数", example="3-5")


class Chapter(BaseModel):
    chapterId: str = Field("", description="章节 ID", example="chap001")
    chapterName: str = Field("", description="章节名称", example="梁弯曲理论基础")
    subChapters: list[SubChapter] = Field(default_factory=list, description="子章节列表")


class StructurePreview(BaseModel):
    chapters: list[Chapter] = Field(default_factory=list, description="章节列表")


class ParseData(BaseModel):
    """课件解析结果"""

    parseId: str = Field("", description="解析任务 ID", example="parse20240520001")
    fileInfo: FileInfo = Field(default_factory=FileInfo, description="文件基本信息")
    structurePreview: StructurePreview = Field(default_factory=StructurePreview, description="知识点结构预览")
    taskStatus: str = Field(
        "processing",
        description="任务状态：processing（处理中）、completed（完成）、failed（失败）",
        example="processing",
    )
    errorMessage: Optional[str] = Field(None, description="错误信息（失败时返回）")


class ScriptSection(BaseModel):
    sectionId: str = Field("", description="章节 ID", example="sec001")
    sectionName: str = Field("", description="章节名称", example="开场白")
    content: str = Field("", description="讲授内容")
    duration: int = Field(0, description="预计讲授时长（秒）", example=15)
    relatedChapterId: str = Field("", description="关联章节 ID")
    relatedPage: Optional[str] = Field(None, description="关联课件页码", example="3-5")
    keyPoints: list[str] = Field(default_factory=list, description="关键知识点")


class ScriptData(BaseModel):
    """讲授脚本数据"""

    scriptId: str = Field("", description="脚本 ID", example="script20240520001")
    scriptStructure: list[ScriptSection] = Field(default_factory=list, description="脚本结构")
    taskStatus: str = Field("processing", description="任务状态", example="processing")
    editUrl: str = Field("", description="脚本编辑地址")
    audioGenerateUrl: str = Field("/api/v1/lesson/generateAudio", description="语音合成接口地址")
    parseId: Optional[str] = Field(None, description="关联解析任务 ID")
    lessonId: Optional[str] = Field(None, description="关联智课 ID")
    teachingStyle: Optional[str] = Field(None, description="讲授风格")
    errorMessage: Optional[str] = Field(None, description="错误信息")

    audioId: Optional[str] = Field(None, description="最新可播放音频任务 ID")
    audioUrl: Optional[str] = Field(None, description="最新可播放音频 URL")


class AudioInfo(BaseModel):
    totalDuration: int = Field(0, description="总时长（秒）", example=600)
    fileSize: int = Field(0, description="文件大小（字节）", example=9600000)
    format: str = Field("mp3", description="音频格式")
    bitRate: int = Field(128000, description="比特率", example=128000)


class SectionAudio(BaseModel):
    sectionId: str = Field("", description="章节 ID", example="sec001")
    audioUrl: str = Field("", description="章节音频 URL")
    duration: int = Field(0, description="时长（秒）", example=15)


class AudioData(BaseModel):
    """语音合成结果"""

    audioId: str = Field("", description="音频任务 ID", example="audio20240520001")
    taskStatus: str = Field("processing", description="任务状态", example="processing")
    audioUrl: Optional[str] = Field(None, description="音频文件 URL")
    audioInfo: Optional[AudioInfo] = Field(None, description="音频信息")
    sectionAudios: list[SectionAudio] = Field(default_factory=list, description="分章节音频信息")
    errorMessage: Optional[str] = Field(None, description="错误信息")


# ── 多模态实时问答模块 ───────────────────────────────────────────────


class RelatedKnowledge(BaseModel):
    knowledgeId: str = Field("", description="知识点 ID", example="know001")
    knowledgeName: str = Field("", description="知识点名称", example="平面假设的工程简化意义")
    relatedSectionId: str = Field("", description="关联章节 ID", example="sec002")


class GamePayloadData(BaseModel):
    """轻量课堂练习数据。"""

    gameType: str = Field("multiple_choice", description="游戏类型", example="multiple_choice")
    prompt: str = Field("", description="题干")
    choices: list[str] = Field(default_factory=list, description="选项列表")
    correctIndex: int = Field(0, description="正确选项下标", example=0)
    correctChoice: str = Field("", description="正确选项文本")
    explanation: str = Field("", description="答案解释")


class QAInteractData(BaseModel):
    """问答交互结果"""

    answerId: str = Field("", description="回答 ID", example="ans20240520001")
    answerContent: str = Field("", description="回答内容")
    answerType: str = Field(
        "text",
        description="回答类型：text（文字）、mixed（图文混合）",
        example="text",
    )
    relatedKnowledge: Optional[RelatedKnowledge] = Field(None, description="关联知识点")
    suggestions: list[str] = Field(default_factory=list, description="追问建议（支持多轮交互）")
    understandingLevel: str = Field(
        "none",
        description="学生理解程度：none（未理解）、partial（部分理解）、full（完全理解）",
        example="partial",
    )
    questionType: str = Field(
        "unknown",
        description="问题类型：definition/reasoning/procedure/example/comparison/summary/unknown",
        example="definition",
    )
    recommendedNarrationLevel: Optional[str] = Field(
        None,
        description="推荐讲解难度档位：A（最详细）/B/C/D（最精简）",
        example="B",
    )
    nextAction: Optional[str] = Field(
        None,
        description="建议下一步教学动作：resume/supplement_then_resume/reteach_slowly/trigger_game",
        example="supplement_then_resume",
    )
    reason: str = Field(
        "",
        description="下一步动作的决策原因",
        example="先补充解释当前知识点，再回到原学习进度。",
    )
    matchedSectionId: Optional[str] = Field(None, description="匹配的章节 ID", example="sec002")
    matchedPage: Optional[int] = Field(None, description="匹配的页码", example=3)
    targetSectionId: Optional[str] = Field(None, description="建议跳转的章节 ID")
    targetPage: Optional[int] = Field(None, description="建议跳转的页码")
    gamePayload: Optional[GamePayloadData] = Field(None, description="小游戏题目数据")


class VoiceToTextData(BaseModel):
    """语音识别结果"""

    text: str = Field("", description="识别文本", example="平面假设为什么能简化梁弯曲问题？")
    confidence: float = Field(0.0, description="识别置信度", example=0.98)
    timestamp: str = Field("", description="识别时间戳", example="2024-05-20 10:05:00")


# ── 学习进度智能适配模块 ─────────────────────────────────────────────


class TrackData(BaseModel):
    """学习进度追踪结果"""

    trackId: str = Field("", description="追踪记录 ID", example="track20240520001")
    totalProgress: float = Field(0.0, description="智课总学习进度（0-100）", example=45.2)
    nextSectionSuggest: str = Field("", description="建议后续学习章节", example="sec002")


class SupplementContent(BaseModel):
    content: str = Field("", description="补充讲解内容")
    duration: int = Field(30, description="补充讲解时长（秒）", example=30)
    relatedExample: str = Field("", description="关联示例")


class NextSection(BaseModel):
    sectionId: str = Field("", description="章节 ID", example="sec002")
    adjustedDuration: int = Field(40, description="调整后时长（秒）", example=75)
    isKeyPointStrengthen: bool = Field(False, description="是否强化重点讲解")


class AdjustPlan(BaseModel):
    continueSectionId: str = Field("", description="续讲章节 ID（定位原讲解节点）", example="sec002")
    adjustType: str = Field(
        "normal",
        description="调整类型：supplement（补充讲解）、accelerate（加速）、normal（正常）",
        example="supplement",
    )
    supplementContent: Optional[SupplementContent] = Field(
        None, description="补充讲解内容（理解程度为 partial 时返回）"
    )
    nextSections: list[NextSection] = Field(default_factory=list, description="后续章节调整建议")


class AdjustData(BaseModel):
    """学习节奏调整结果"""

    adjustPlan: AdjustPlan = Field(default_factory=AdjustPlan, description="调整方案")


# ── 平台对接模块 ─────────────────────────────────────────────────────


class SyncCourseData(BaseModel):
    """课程同步结果"""

    internalCourseId: str = Field("", description="系统内部课程 ID", example="cou30001")
    syncStatus: str = Field("success", description="同步状态", example="success")
    syncTime: str = Field("", description="同步时间", example="2024-05-20 11:00:00")


class SyncUserData(BaseModel):
    """用户同步结果"""

    internalUserId: str = Field("", description="系统内部用户 ID", example="stu20001")
    syncStatus: str = Field("success", description="同步状态", example="success")
    authToken: str = Field("", description="身份验证令牌")


# ── 智课生成扩展（流水线 + PPT 渲染）────────────────────────────────


class RenderData(BaseModel):
    """PPT 渲染结果"""

    lessonId: str = Field("", description="智课 ID", example="lesson20240520001")
    taskStatus: str = Field("processing", description="渲染状态", example="processing")
    renderedPptUrl: Optional[str] = Field(None, description="渲染后 PPTX 下载地址")
    errorMessage: Optional[str] = Field(None, description="错误信息")


class WorkflowStepInfo(BaseModel):
    step: str = Field("", description="步骤名称", example="课件解析")
    status: str = Field("pending", description="步骤状态", example="completed")
    detail: Optional[str] = Field(None, description="详细信息（错误时为错误描述）")


class WorkflowData(BaseModel):
    """一键智课生成流水线结果"""

    lessonId: str = Field("", description="智课 ID", example="lesson20240520001")
    lessonName: str = Field("", description="智课名称")
    workflowStatus: str = Field(
        "processing",
        description="流水线总状态：processing（执行中）、completed（完成）、failed（失败）",
        example="processing",
    )
    steps: list[WorkflowStepInfo] = Field(default_factory=list, description="各步骤执行状态")
    parseId: Optional[str] = Field(None, description="解析任务 ID")
    scriptId: Optional[str] = Field(None, description="脚本 ID")
    renderedPptUrl: Optional[str] = Field(None, description="渲染后 PPTX 下载地址")
    errorMessage: Optional[str] = Field(None, description="错误信息")
