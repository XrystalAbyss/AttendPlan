import type {CourseRecord} from "./types/attendance";
export function standing(course: Pick<CourseRecord,"attended"|"delivered"|"is_lab">) {
  if (!course.delivered) return {status:"UNRECORDED",bunks:null};
  if (course.attended*4 < course.delivered*3) return {status:"AT_RISK",bunks:0};
  const periods = Math.floor((course.attended*4-course.delivered*3)/3);
  const bunks = Math.floor(periods/(course.is_lab ? 2 : 1));
  return {status:bunks===0 ? "CAUTION" : "SAFE",bunks};
}
