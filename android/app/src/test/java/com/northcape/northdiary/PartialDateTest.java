package com.northcape.northdiary;
import org.junit.Test;
import static org.junit.Assert.*;

public class PartialDateTest {
    @Test public void desktopPartialDatesRoundTrip(){
        assertEquals("2026-未知-未知",PartialDate.normalize("2026"));
        assertEquals("2026-11-未知",PartialDate.normalize("2026-11"));
        assertEquals("2024-02-29",PartialDate.normalize("2024-02-29"));
        assertEquals("2026年",PartialDate.label("2026-未知-未知"));
        assertEquals("2026年11月",PartialDate.label("2026-11-未知"));
    }
    @Test public void invalidDatesAreRejected(){
        for(String s:new String[]{"2026-02-29","2026-13","2026-未知-15","0000","26","2026-1","2026-11-31","2026-11-01xxx"}) {
            try{PartialDate.normalize(s);fail(s);}catch(IllegalArgumentException expected){}
        }
    }
}
