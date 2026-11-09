import type { Requirement, TestCase } from "./types";

/** 真实需求：来自 App/data/ratgp.db（CR-001 ~ CR-025） */
export const requirements: Requirement[] = [
  {"id": "CR-001", "title": "登录认证", "desc": "学生、教师、管理员分别使用学号/工号+密码登录；连续5次失败锁定10分钟。", "type": "functional", "acc": ["学生使用学号+密码登录成功", "教师使用工号+密码登录成功", "管理员使用工号+密码登录成功", "连续5次登录失败后账户锁定10分钟", "锁定期间正确密码也无法登录"], "risks": [], "status": "confirmed", "para": 3, "ratio": 0.949, "raw": "学生、教师、管理员分别使用学号/工号+密码登录；连续 5 次失败锁定 10 分钟。", "covered": true},
  {"id": "CR-002", "title": "课程查询", "desc": "学生可按课程名称、教师、院系、上课时间组合查询本学期课程，结果分页每页20条。", "type": "functional", "acc": ["支持按课程名称、教师、院系、上课时间的任意组合查询", "查询结果仅包含本学期课程", "结果分页展示，每页20条"], "risks": [], "status": "confirmed", "para": 5, "ratio": 0.975, "raw": "学生可按课程名称、教师、院系、上课时间组合查询本学期课程，结果分页每页 20 条。", "covered": true},
  {"id": "CR-003", "title": "选课时间窗口", "desc": "选课窗口为每学期第1周周一8:00至第2周周五18:00，窗口外不可选课。", "type": "functional", "acc": ["窗口内允许选课", "窗口开始前拒绝选课", "窗口结束后拒绝选课"], "risks": [], "status": "confirmed", "para": 7, "ratio": 0.914, "raw": "选课窗口为每学期第 1 周周一 8:00 至第 2 周周五 18:00，窗口外不可选课。", "covered": true},
  {"id": "CR-004", "title": "时间冲突校验", "desc": "提交选课时校验同一时间段课程冲突；冲突则拒绝并提示冲突课程。", "type": "functional", "acc": ["选课时间与已选课程无冲突时允许提交", "存在时间冲突时拒绝选课", "拒绝时提示具体冲突课程"], "risks": [], "status": "confirmed", "para": 9, "ratio": 1.0, "raw": "提交选课时校验同一时间段课程冲突；冲突则拒绝并提示冲突课程。", "covered": true},
  {"id": "CR-005", "title": "先修课校验", "desc": "选课前校验先修课，未通过先修课的学生不得选择该课程。", "type": "functional", "acc": ["已通过先修课的学生允许选课", "未通过先修课的学生拒绝选课"], "risks": [], "status": "confirmed", "para": 11, "ratio": 1.0, "raw": "选课前校验先修课，未通过先修课的学生不得选择该课程。", "covered": true},
  {"id": "CR-006", "title": "选课门数上限", "desc": "每学期每名学生最多选6门课程，第7门应拒绝。", "type": "functional", "acc": ["已选课程少于6门时允许选课", "已选课程达到6门时拒绝第7门选课"], "risks": [], "status": "confirmed", "para": 13, "ratio": 0.917, "raw": "每学期每名学生最多选 6 门课程，第 7 门应拒绝。", "covered": true},
  {"id": "CR-007", "title": "退课截止", "desc": "退课截止时间为第2周周五18:00，截止后不可退课。", "type": "functional", "acc": ["截止时间前允许退课", "截止时间后拒绝退课"], "risks": [], "status": "confirmed", "para": 15, "ratio": 0.945, "raw": "退课截止时间为第 2 周周五 18:00，截止后不可退课。", "covered": true},
  {"id": "CR-008", "title": "课程容量", "desc": "课程默认容量50人，管理员不得扩容；第51人选课应拒绝。", "type": "functional", "acc": ["课程默认容量为50人", "已选人数小于50时允许选课", "已选人数达到50时拒绝第51人选课", "管理员无法扩容课程容量"], "risks": [], "status": "confirmed", "para": 17, "ratio": 0.933, "raw": "课程默认容量 50 人，管理员不得扩容；第 51 人选课应拒绝。", "covered": true},
  {"id": "CR-009", "title": "成绩发布后不可改", "desc": "成绩录入并发布后不可修改；如需更正走线下审批。", "type": "functional", "acc": ["成绩发布前允许修改", "成绩发布后拒绝修改", "成绩发布后提供线下审批更正说明"], "risks": [], "status": "confirmed", "para": 19, "ratio": 1.0, "raw": "成绩录入并发布后不可修改；如需更正走线下审批。", "covered": true},
  {"id": "CR-010", "title": "教师开课申请", "desc": "教师可提交开课申请，填写课程名、学分、容量、时间、地点、先修课，提交后待审。", "type": "functional", "acc": ["教师可填写课程名、学分、容量、时间、地点、先修课并提交", "提交后申请状态为待审核"], "risks": [], "status": "confirmed", "para": 21, "ratio": 1.0, "raw": "教师可提交开课申请，填写课程名、学分、容量、时间、地点、先修课，提交后待审。", "covered": true},
  {"id": "CR-011", "title": "管理员审核开课", "desc": "管理员审核开课申请，通过后课程进入可选列表；拒绝需填写原因。", "type": "functional", "acc": ["管理员可通过开课申请，通过后课程进入可选列表", "管理员可拒绝开课申请，拒绝时必须填写原因"], "risks": [], "status": "confirmed", "para": 23, "ratio": 1.0, "raw": "管理员审核开课申请，通过后课程进入可选列表；拒绝需填写原因。", "covered": true},
  {"id": "CR-012", "title": "成绩查询", "desc": "学生可查询本人已选课程和已发布成绩，不能查看他人成绩。", "type": "functional", "acc": ["学生可查询本人已选课程", "学生可查询本人已发布成绩", "学生无法查看他人成绩"], "risks": [], "status": "confirmed", "para": 25, "ratio": 1.0, "raw": "学生可查询本人已选课程和已发布成绩，不能查看他人成绩。", "covered": true},
  {"id": "CR-013", "title": "选课结果通知", "desc": "选课结果生成后5分钟内发送站内信，失败重试3次。", "type": "functional", "acc": ["选课结果生成后5分钟内发送站内信", "发送失败时重试最多3次"], "risks": [], "status": "confirmed", "para": 27, "ratio": 0.923, "raw": "选课结果生成后 5 分钟内发送站内信，失败重试 3 次。", "covered": true},
  {"id": "CR-014", "title": "统计报表导出", "desc": "管理员可导出选课统计CSV，字段含课程、容量、已选人数、选课率，使用UTF-8 BOM。", "type": "functional", "acc": ["管理员可导出选课统计CSV", "CSV字段包含课程、容量、已选人数、选课率", "CSV文件使用UTF-8 BOM编码"], "risks": [], "status": "confirmed", "para": 29, "ratio": 0.978, "raw": "管理员可导出选课统计 CSV，字段含课程、容量、已选人数、选课率，使用 UTF-8 BOM。", "covered": true},
  {"id": "CR-015", "title": "系统响应快速", "desc": "系统响应快速，学生查询课程时无明显等待。", "type": "non_functional", "acc": ["学生查询课程时无明显等待（需进一步量化响应时间指标）"], "risks": ["ambiguous"], "status": "unconfirmed", "para": 31, "ratio": 1.0, "raw": "系统响应快速，学生查询课程时无明显等待。", "covered": true},
  {"id": "CR-016", "title": "界面友好美观", "desc": "系统界面友好美观，操作便捷。", "type": "non_functional", "acc": ["界面友好美观、操作便捷（需进一步明确可度量标准）"], "risks": ["ambiguous"], "status": "unconfirmed", "para": 33, "ratio": 1.0, "raw": "系统界面友好美观，操作便捷。", "covered": false},
  {"id": "CR-017", "title": "通知及时", "desc": "选课结果通知应及时，确保学生尽快知晓。", "type": "non_functional", "acc": ["选课结果通知及时送达（需进一步量化时限指标）"], "risks": ["ambiguous"], "status": "unconfirmed", "para": 35, "ratio": 1.0, "raw": "选课结果通知应及时，确保学生尽快知晓。", "covered": false},
  {"id": "CR-018", "title": "课程推荐合理", "desc": "系统能根据学生兴趣推荐合理课程。", "type": "functional", "acc": ["系统根据学生兴趣推荐课程（需进一步明确推荐合理性标准）"], "risks": ["ambiguous"], "status": "unconfirmed", "para": 37, "ratio": 1.0, "raw": "系统能根据学生兴趣推荐合理课程。", "covered": false},
  {"id": "CR-019", "title": "高并发稳定", "desc": "系统在高并发选课期间保持稳定。", "type": "non_functional", "acc": ["高并发选课期间系统保持稳定（需进一步量化并发量与稳定性指标）"], "risks": ["ambiguous"], "status": "unconfirmed", "para": 39, "ratio": 1.0, "raw": "系统在高并发选课期间保持稳定。", "covered": false},
  {"id": "CR-020", "title": "选课公平高效", "desc": "选课过程应公平高效，避免拥堵。", "type": "non_functional", "acc": ["选课过程公平高效、避免拥堵（需进一步明确公平与效率的度量标准）"], "risks": ["ambiguous"], "status": "unconfirmed", "para": 41, "ratio": 1.0, "raw": "选课过程应公平高效，避免拥堵。", "covered": false},
  {"id": "CR-021", "title": "允许选8门", "desc": "允许学生每学期选8门课程。", "type": "functional", "acc": ["学生每学期可选8门课程（与CR-006最多6门矛盾，需澄清）"], "risks": ["conflict"], "status": "unconfirmed", "para": 43, "ratio": 0.929, "raw": "允许学生每学期选 8 门课程。", "covered": false},
  {"id": "CR-022", "title": "四周内可退课", "desc": "开学后4周内学生可无条件退课。", "type": "functional", "acc": ["开学后4周内允许无条件退课（与CR-007第2周周五18:00截止矛盾，需澄清）"], "risks": ["conflict"], "status": "unconfirmed", "para": 45, "ratio": 0.938, "raw": "开学后 4 周内学生可无条件退课。", "covered": false},
  {"id": "CR-023", "title": "热门课程自动扩容", "desc": "热门课程可根据选课人数自动扩容至100人。", "type": "functional", "acc": ["热门课程根据选课人数自动扩容至100人（与CR-008默认容量50且不得扩容矛盾，需澄清）"], "risks": ["conflict"], "status": "unconfirmed", "para": 47, "ratio": 0.955, "raw": "热门课程可根据选课人数自动扩容至 100 人。", "covered": false},
  {"id": "CR-024", "title": "成绩7天内可改", "desc": "教师可在成绩发布后7天内任意修改成绩。", "type": "functional", "acc": ["成绩发布后7天内教师可修改成绩（与CR-009发布后不可改矛盾，需澄清）"], "risks": ["conflict"], "status": "unconfirmed", "para": 49, "ratio": 0.95, "raw": "教师可在成绩发布后 7 天内任意修改成绩。", "covered": false},
  {"id": "CR-025", "title": "容量无限扩容", "desc": "课程容量可根据需求无限扩容。", "type": "functional", "acc": ["课程容量可根据需求无限扩容（与CR-008不得扩容、CR-023扩容至100人矛盾，需澄清）"], "risks": ["conflict"], "status": "unconfirmed", "para": 51, "ratio": 1.0, "raw": "课程容量可根据需求无限扩容。", "covered": false},
];

/** 示例用例：M4 尚未实现，P1 只用于把界面跑起来 */
export const cases: TestCase[] = [
  {"id": "TC-001", "title": "教师登录成功并校验角色权限", "type": "normal", "reqs": ["CR-001"]},
  {"id": "TC-002", "title": "连续 5 次失败后锁定账户 10 分钟", "type": "abnormal", "reqs": ["CR-001"]},
  {"id": "TC-003", "title": "按课程名 / 教师 / 院系组合查询并分页", "type": "normal", "reqs": ["CR-002"]},
  {"id": "TC-004", "title": "选课窗口开始前提交被拒", "type": "abnormal", "reqs": ["CR-003"]},
  {"id": "TC-005", "title": "退课截止时间边界：18:00 前与后", "type": "boundary", "reqs": ["CR-007"]},
  {"id": "TC-006", "title": "时间冲突时拒绝并提示冲突课程", "type": "abnormal", "reqs": ["CR-004"]},
  {"id": "TC-007", "title": "未通过先修课的学生选课被拒", "type": "abnormal", "reqs": ["CR-005"]},
  {"id": "TC-008", "title": "已选 6 门后提交第 7 门被拒", "type": "boundary", "reqs": ["CR-006"]},
  {"id": "TC-009", "title": "容量 50 人上限边界", "type": "boundary", "reqs": ["CR-008"]},
  {"id": "TC-010", "title": "成绩发布后修改被拒", "type": "abnormal", "reqs": ["CR-009"]},
  {"id": "TC-011", "title": "学生仅能查询本人成绩", "type": "normal", "reqs": ["CR-012"]},
  {"id": "TC-012", "title": "开课申请提交与必填校验", "type": "normal", "reqs": ["CR-010", "CR-011"]},
  {"id": "TC-013", "title": "统计 CSV 导出字段与 UTF-8 BOM", "type": "normal", "reqs": ["CR-013", "CR-014", "CR-015"]},
];

