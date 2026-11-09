export type Risk = "ambiguous" | "conflict";
export type ReqStatus = "confirmed" | "unconfirmed";
export type ReqType = "functional" | "non_functional";
export type CaseType = "normal" | "abnormal" | "boundary";

export interface Requirement {
  id: string;
  title: string;
  desc: string;
  type: ReqType;
  acc: string[];
  risks: Risk[];
  status: ReqStatus;
  /** 原文段落号（Document.para_index） */
  para: number;
  /** 段落匹配相似度 0–1 */
  ratio: number;
  /** 来源段落原文 */
  raw: string;
  covered: boolean;
}

export interface TestCase {
  id: string;
  title: string;
  type: CaseType;
  /** 关联的需求编号 */
  reqs: string[];
}
