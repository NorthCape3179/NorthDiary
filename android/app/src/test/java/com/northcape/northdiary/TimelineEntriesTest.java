package com.northcape.northdiary;

import org.junit.Test;
import java.util.*;
import static org.junit.Assert.*;
import static com.northcape.northdiary.Models.*;
import static com.northcape.northdiary.TimelineEntries.*;

public class TimelineEntriesTest {
    private Article article(String id,String date){Article a=new Article();a.id=id;a.title=id;a.date=date;return a;}
    @Test public void groupsOnlyRealYearsMonthsAndKeepsUnknownPrecision(){
        List<Entry> e=TimelineEntries.build(Arrays.asList(article("day","2026-11-02"),article("month","2026-11"),article("year","2026"),article("old","2024-02-29")));
        List<String> labels=new ArrayList<>();for(Entry row:e)labels.add(row.kind+":"+row.label);
        assertEquals(Arrays.asList("YEAR:2026 年","MONTH:11 月","ARTICLE:2 日","ARTICLE:日期未详","MONTH:月份未详","ARTICLE:仅记得年份","YEAR:2024 年","MONTH:2 月","ARTICLE:29 日"),labels);
        assertEquals(3,e.get(0).count);assertEquals(2,e.get(1).count);
    }
    @Test public void excludesOutsideDraftAndTrashAndSortsLatestFirst(){
        Article outside=article("outside","2027");outside.outside=true;Article draft=article("draft","2028");draft.draft=true;Article trash=article("trash","2029");trash.deleted=true;
        List<Entry> e=TimelineEntries.build(Arrays.asList(outside,draft,trash,article("old","2020"),article("new","2026-12-01")));
        List<String> ids=new ArrayList<>();for(Entry row:e)if(row.article!=null)ids.add(row.article.id);
        assertEquals(Arrays.asList("new","old"),ids);assertEquals("2026 年",e.get(0).label);
    }
    @Test public void emptyArchiveHasNoEmptyHeaders(){assertTrue(TimelineEntries.build(Collections.emptyList()).isEmpty());}
    @Test public void sameDayHasStableIdentityOrderWithoutChangingSource(){
        Article b=article("b","2026-01-01"),a=article("a","2026-01-01");List<Article> input=Arrays.asList(b,a);
        List<Entry> e=TimelineEntries.build(input);assertEquals("a",e.get(2).article.id);assertEquals("b",input.get(0).id);
    }
}
