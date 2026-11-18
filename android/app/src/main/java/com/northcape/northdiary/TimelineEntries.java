package com.northcape.northdiary;

import java.util.*;
import static com.northcape.northdiary.Models.*;

/** One shared chronology for drawing, year jumps and tests; partial dates stay partial. */
final class TimelineEntries {
    enum Kind {YEAR, MONTH, ARTICLE}
    static final class Entry {
        final Kind kind;
        final String year,month,label;
        final Article article;
        final int count;
        Entry(Kind kind,String year,String month,String label,Article article,int count){
            this.kind=kind;this.year=year;this.month=month;this.label=label;this.article=article;this.count=count;
        }
    }
    private static final class Dated {
        final Article article;final String date;
        Dated(Article article){this.article=article;date=PartialDate.normalize(article.date);}
    }
    static List<Entry> build(List<Article> source){
        List<Dated> sorted=new ArrayList<>();
        for(Article article:source)if(!article.outside&&!article.draft&&!article.deleted)sorted.add(new Dated(article));
        sorted.sort(Comparator.comparing((Dated a)->a.date.replace("未知","00")).reversed().thenComparing(a->a.article.id));
        Map<String,Integer> years=new HashMap<>(),months=new HashMap<>();
        for(Dated a:sorted){String y=a.date.substring(0,4),m=a.date.substring(0,7);years.put(y,years.getOrDefault(y,0)+1);months.put(m,months.getOrDefault(m,0)+1);}
        List<Entry> entries=new ArrayList<>();String year="",month="";
        for(Dated a:sorted){
            String[] parts=a.date.split("-");String y=parts[0],m=parts[1];
            if(!year.equals(y)){entries.add(new Entry(Kind.YEAR,y,"",y+" 年",null,years.get(y)));year=y;month="";}
            if(!month.equals(m)){entries.add(new Entry(Kind.MONTH,y,m,m.equals("未知")?"月份未详":Integer.parseInt(m)+" 月",null,months.get(a.date.substring(0,7))));month=m;}
            String label=m.equals("未知")?"仅记得年份":parts[2].equals("未知")?"日期未详":Integer.parseInt(parts[2])+" 日";
            entries.add(new Entry(Kind.ARTICLE,y,m,label,a.article,1));
        }
        return entries;
    }
    private TimelineEntries(){}
}
