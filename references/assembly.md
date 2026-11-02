# 组装配置与能力

在同一个Python环境中检查依赖并执行脚本。先运行`python scripts/check_environment.py`，输出解释器路径和真实导入结果；非零退出表示需解决依赖，不能把环境检查当作PPT验收。

大纲阶段运行`python scripts/validate_project.py --project <项目目录> --stage draft`检查配置，允许尚未生成的主体与叠加素材缺失，但指定的Logo原始输入仍须存在；已存在的图片仍会检查。交付前使用默认`--stage ready`，要求全部图片齐全。组装始终执行ready检查，不能凭draft通过宣称成品可用。颜色为不带#的六位十六进制字符串，字号为正数；固定标题、页码与Logo区域彼此不能重叠；overlay主体可以覆盖全画布，framed主体仍须避开固定元素。

现有项目配置继续有效。`size` 是画布英寸尺寸；`mode` 为 `layered` 或 `full`。`style` 为正文全局样式；新增`layouts`保存命名样式字典，每页用`layout`引用名称。按“全局style → layouts[layout] → 本页style”浅合并，数组字段整体替换；未指定layout保持旧行为，引用不存在名称报错。坐标框为 `[左, 上, 宽, 高]`，单位英寸。

## 页型与模式选择

`type` 使用 `cover`（封面）、`contents`（目录）、`section`（章节过渡）、`closing`（结束）或 `content`（正文）。根据页面用途分类，不仅凭页码判断。大纲阶段先解析用户要求，再逐页显式写入最终`mode`，使提示词和配置一致。

优先级：
1. 用户明确指定的逐页模式优先；要求“所有页必须分层”时将每页明确写为`layered`。
2. 用户指定整套整页生图时，每页使用`full`。
3. 采用分层组装方案时，四类特殊页默认`full`，正文默认`layered`。仅说“分层组装”不意味着所有页都必须分层。

脚本按显式逐页`mode`优先；未写逐页模式时，全局`full`全部整页，全局`layered`下已标注的四类特殊页自动使用`full`，其余继承正文模式。旧配置缺少`type`时保留原有行为，不猜测标题或页码；旧配置已显式写`layered`的特殊页须在项目修订时主动改成`full`，脚本不擅自覆盖。

整页图片完整等比放到全画布，按画布比例生成才能铺满；比例不符时检查并重新生成，不能用拉伸或裁字强行铺满。插入整页图片是输出PPT所需的封装步骤，不是套用正文分层模板。不会自动加顶部标题、底部Logo和页码。整页如须原样保留Logo，可用该页`overlays`插入原图，位置由该页构图确定；不使用正文`logo_box`作为默认位置。

逐页样式支持 `title_box`、`content_box`、`logo_box`、`page_box`、`background`、`color`、`font`、`title_size`、`page_size`。用页型对应的已确认样式配置封面、正文等，不随机逐页改动固定元素。标题支持显式换行，框高须足够且最终渲染检查。只有layered模式添加固定标题、Logo和页码，full模式的文字已包含在整页图中。

全局 `logo` 指向原始图片；每页可用 `logo` 指定另一素材或 `null` 表示本页不加Logo。未写则继承全局。Logo等比完整放入配置框；框大小不等于图片实际可见大小，需要在组装样张确认。
上述`logo`与`logo_box`仅用于分层页；整页模式忽略它们，需要的原图通过显式`overlays`添加。

准确公式、数据表等使用每页可选的 `overlays` 图片素材列表，按列表顺序叠加到主体上，再添加固定元素。例如：

```json
{
  "id": "06",
  "title": "模板用量与稀释计算",
  "image": "images/06.png",
  "mode": "layered",
  "overlays": [
    {"image": "assets/formula-06.png", "box": [1.0, 1.3, 4.0, 0.6]}
  ]
}
```

独立素材保持比例，可保留透明背景。分层framed时素材必须位于content_box内，overlay时位于画布内；两者均不能覆盖固定元素；生图提示词须保留对应区域并排除重复文字。若出现大面积留空影响构图，先考虑让模型直接生成并核对内容，或重新规划素材区域。工具生成公式素材之后检查实际符号和上下标，不以使用了确定性工具代替内容校对。

脚本只组装现成图片与固定文字，不生成公式、插画或可交互题目，也不检查标题溢出、图片内文字正确性或专业事实。图片比例与框明显不符时发出适配提示；完整等比放置会产生空隙，仍须通过实际PPT渲染检查。

## 整页设计字段

新字段均放在style或layouts中的样式字典内。背景、标签和显示状态也可由逐页style覆盖。新模板只展示可调整起点，不代表用户已经选定其颜色与坐标。三种命名版式以16:9为例，改画布比例后须重新设计框位。

- `background_image`：背景素材路径，相对项目目录；仅分层页使用，null取消继承。按整画布比例完整适配，比例不符会提示留白。纯色background仍作为底层。full页忽略正文背景图、装饰与固定层。
- `content_surface`：transparent、matched或panel。未设置时保持旧行为；transparent必须是真实含透明像素且非完全透明的图；matched使用同底色并人工检查接缝；panel仅在用户选择有意分区时使用。草稿允许缺失未来素材，但已有图会检查。
- 对title/page/section各角色可设置`*_font`、`*_size`、`*_color`、`*_align`（left/center/right）和`*_bold`。字体颜色默认继承font/color，标题30pt、页码和章节12pt。未写对齐字段保留旧版文本框行为。
- `show_title`、`show_page`、`show_logo`、`show_section`为布尔开关，默认true。章节仅在`section_text`非空时显示，并需提供`section_box`；可以通过逐页style给不同章节赋值。不显示的固定元素不参与位置相交校验。
- `page_format`默认`{n}`，可写`{n} / {total}`；n为实际幻灯片序号，total为整套页数，包含特殊页。只支持这两个占位符，不支持任意字段、属性访问或格式表达式。
- `accents`为可选列表，只支持line或rect。每项提供`type`、`box`和六位十六进制`color`；line的box表示起点x/y及终点增量w/h，允许水平/垂直线，width是正数pt线宽；rect使用普通正宽高框。数组浅覆盖，不累计。其为明确底层装饰，允许与内容区域交叠，不纳入固定内容碰撞检查；文字可读性仍须视觉核验。

渲染顺序：纯色底 → 分层background_image → accents → 主体图片 → overlays → 显示的标题/页码/章节 → 原始Logo。背景图、透明PNG及叠加素材保持比例，alpha随素材保留；不做抠图或白色像素删除。新增背景路径ready必须存在，draft允许其为未来产物。Logo为实际输入素材，显示时draft也须存在。

示例：将某正文页设为`"layout":"editorial"`；在其style内设置`"section_text":"实验设计"`和`"content_surface":"matched"`。换布局后先更新正文比例与提示词再重做样张，不能指望旧主体图自动适配所有布局。

## 正文图文归属

framed使用content_surface=matched作为默认衔接方案，它不表示正文无文字；overlay无需外围同色拼接，模板保留matched只表示不强制透明。framed的content_box容纳整个正文图文画面，不预留统一左侧正文文本栏。组装器保持只添加固定文字，不新增批量正文文本框；正文展示文字应已在image内。overlays仅用于必要精确素材，不能默认拆出全部正文。既有transparent配置保留，旧项目不自动迁移。样张检查同时查看正文原图与组装结果，结构校验无法证明图片内正文存在或正确。

## composition构图与局部预留

style（可由命名layout或本页style覆盖）新增composition，只允许framed或overlay。未写时framed以兼容旧配置；新模板示例使用canvas-local的overlay，三个传统版式显式framed作为备选。不能自动迁移旧项目。

framed继续读取content_box，保护其与固定元素的非重叠。overlay忽略content_box，主体按[0,0,画布宽,画布高]完整等比放置，图片比例需匹配，不拉伸或裁字。full不受composition影响，不添加分层固定元素。

运行python scripts/describe_layout.py --project <目录> --slide-id <标识>可在生成前获得实际图片框、目标比例、已启用固定角色的坐标（英寸和百分比）。同一title_box、logo_box、page_box、section_box既供提示词导出又供组装使用，没有第二份预留坐标。导出不检查图片存在或是否已生成，不能视作视觉验收。

overlay保持原有绘制顺序：底层背景/装饰（如有）→全画布图文图片→精确overlays→原生标题/页码/章节→原始Logo。全画布不透明图片会遮住底层背景和装饰，应把所需背景视觉直接纳入生成图；不要以为底层线条会自动浮到图上。overlay不需要同色拼接，只有透明时才会透出底层。

校验允许overlay主体框与固定角色框重叠，仍检查边界、角色彼此冲突和精确overlays侵占角色框。图片内的文字与关键图示是否侵入角色框只能结合原图、OCR辅助及最终渲染检查，不能由矩形校验保证。

## 整套正文设计锁

可选body_design示例：{"layout":"canvas-local","reference_image":"assets/approved-reference.png","locked":false}。可选style为全套统一覆盖，必须同样应用到正文有效style。用户明确确认完整样张后，将status.samples记录为confirmed，再运行python scripts/lock_design.py --project <目录>。禁止智能体自行将未确认样张标confirmed。

锁记录fingerprint涵盖画布、固定元素有效设置、Logo文件内容及完整参考图版本；校验每页有效设置，不以布局名称判断一致。正文标题、页码实际值、章节名称可以不同。原配置没有body_design保持兼容。locked=false表示样张阶段，不是成品设计已通过。

正文full例外必须由用户明确选择后记录body_design_exception=true；校验会提示该页不受原生布局锁保护。修改全套设计需更新样张、重新确认与锁摘要，并将旧生成图列为需重新检查或生成；不靠更新摘要绕过审阅。参考图应是已确认的最终组装页面，生图工具实际需要收到该图而非仅其路径文字。

运行测试：python -m unittest discover -s tests -v。图文融合、标题溢出与对比度仍靠实际渲染检查，不由布局锁证明。


正文生成、批量检查和组装须读取 [body-consistency.md](body-consistency.md)：统一标题、Logo与分隔线，正文按内容量安排重心，并检查模式和主标题归属。新项目优先采用该规则；旧项目不自动迁移。
