import {expect,it} from "vitest";
import {standing} from "../standing";
it("uses exact 75 percent standing and whole two-period lab sessions",()=>{
 expect(standing({attended:74,delivered:100,is_lab:false}).status).toBe("AT_RISK");
 expect(standing({attended:75,delivered:100,is_lab:false}).status).toBe("CAUTION");
 expect(standing({attended:76,delivered:100,is_lab:false}).status).toBe("SAFE");
 expect(standing({attended:76,delivered:100,is_lab:true}).status).toBe("CAUTION");
 expect(standing({attended:77,delivered:100,is_lab:true}).status).toBe("SAFE");
 expect(standing({attended:0,delivered:0,is_lab:true}).status).toBe("UNRECORDED");
});
