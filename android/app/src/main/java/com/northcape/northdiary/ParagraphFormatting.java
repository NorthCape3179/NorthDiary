package com.northcape.northdiary;

import android.content.Context;
import android.text.*;
import android.text.style.*;
import java.util.*;
import java.util.regex.*;

/** Visual first-line indent and per-paragraph alignment, round-tripped as normal HTML. */
final class ParagraphFormatting {
    private static final String MARKER="<!--northdiary-paragraphs-v1-->";
    private static final Pattern PARAGRAPH=Pattern.compile("<p\\b([^>]*)>(.*?)</p>",Pattern.CASE_INSENSITIVE|Pattern.DOTALL);
    static final class Indent extends LeadingMarginSpan.Standard {Indent(int width){super(width,0);}}
    static int indentWidth(Context c){return Math.round(34*c.getResources().getDisplayMetrics().scaledDensity);}
    static SpannableStringBuilder parse(Context c,String html){
        SpannableStringBuilder result;
        if(html.contains(MARKER)){
            result=new SpannableStringBuilder();Matcher matcher=PARAGRAPH.matcher(html);List<String> attrs=new ArrayList<>();List<Integer> starts=new ArrayList<>();
            while(matcher.find()){
                if(!attrs.isEmpty())result.append('\n');starts.add(result.length());attrs.add(matcher.group(1));
                String inner=matcher.group(2);if(!inner.matches("(?is)\\s*<br\\s*/?>\\s*"))result.append(Html.fromHtml(inner,Html.FROM_HTML_MODE_COMPACT));
            }
            for(int i=0;i<attrs.size();i++)applyAttrs(c,result,attrs.get(i),starts.get(i),i+1<starts.size()?starts.get(i+1):result.length());
        }else{
            result=new SpannableStringBuilder(Html.fromHtml(html,Html.FROM_HTML_MODE_COMPACT));
            Matcher matcher=PARAGRAPH.matcher(html);int cursor=0;
            while(matcher.find()){
                String text=Html.fromHtml(matcher.group(2),Html.FROM_HTML_MODE_COMPACT).toString().replaceAll("\\n+$","");
                if(text.isEmpty())continue;int start=result.toString().indexOf(text,cursor);if(start<0)continue;
                int end=start+text.length();if(end<result.length()&&result.charAt(end)=='\n')end++;
                if(start==0||result.charAt(start-1)=='\n')applyAttrs(c,result,matcher.group(1),start,end);cursor=end;
            }
        }
        return result;
    }
    private static void applyAttrs(Context c,Spannable text,String attrs,int start,int end){
        if(attrs.matches("(?is).*text-align\\s*:\\s*center.*")||attrs.matches("(?is).*align\\s*=\\s*['\"]?center.*"))
            text.setSpan(new AlignmentSpan.Standard(Layout.Alignment.ALIGN_CENTER),start,end,Spanned.SPAN_PARAGRAPH);
        else if(attrs.matches("(?is).*text-indent\\s*:\\s*2em.*")||attrs.contains("data-ndiary-indent=\"2\""))
            text.setSpan(new Indent(indentWidth(c)),start,end,Spanned.SPAN_PARAGRAPH);
    }
    private static int lineStart(CharSequence text,int at){int start=Math.max(0,Math.min(at,text.length()));while(start>0&&text.charAt(start-1)!='\n')start--;return start;}
    private static int lineEnd(CharSequence text,int at){int end=Math.max(0,Math.min(at,text.length()));while(end<text.length()&&text.charAt(end)!='\n')end++;return end<text.length()?end+1:end;}
    private static boolean centered(Spanned text,int start,int end){
        for(AlignmentSpan span:text.getSpans(start,end,AlignmentSpan.class))if(text.getSpanStart(span)<=start&&text.getSpanEnd(span)>=end&&span.getAlignment()==Layout.Alignment.ALIGN_CENTER)return true;
        return false;
    }
    static void autoIndent(Editable text,boolean enabled,int width){
        for(Indent span:text.getSpans(0,text.length(),Indent.class))text.removeSpan(span);
        int start=0;
        while(start<text.length()){
            int end=lineEnd(text,start);if(enabled&&!centered(text,start,end))text.setSpan(new Indent(width),start,end,Spanned.SPAN_PARAGRAPH);
            start=end;
        }
    }
    static void toggleCenter(Editable text,int from,int to,boolean indent,int width){
        int start=lineStart(text,from),end=lineEnd(text,to>from&&to>0&&text.charAt(to-1)=='\n'?to-1:to);
        boolean clear=centered(text,start,end);
        for(AlignmentSpan span:text.getSpans(start,end,AlignmentSpan.class)){
            int left=text.getSpanStart(span),right=text.getSpanEnd(span);text.removeSpan(span);
            if(left<start)text.setSpan(new AlignmentSpan.Standard(span.getAlignment()),left,start,Spanned.SPAN_PARAGRAPH);
            if(right>end)text.setSpan(new AlignmentSpan.Standard(span.getAlignment()),end,right,Spanned.SPAN_PARAGRAPH);
        }
        if(!clear)text.setSpan(new AlignmentSpan.Standard(Layout.Alignment.ALIGN_CENTER),start,end,Spanned.SPAN_PARAGRAPH);
        autoIndent(text,indent,width);
    }
    static String html(Spanned text){
        StringBuilder html=new StringBuilder(MARKER);int start=0;
        do{
            int newline=text.toString().indexOf('\n',start),end=newline<0?text.length():newline;
            SpannableStringBuilder fragment=new SpannableStringBuilder(text.subSequence(start,end));
            for(ParagraphStyle style:fragment.getSpans(0,fragment.length(),ParagraphStyle.class))fragment.removeSpan(style);
            String inline=fragment.length()==0?"<br>":Html.toHtml(fragment,Html.TO_HTML_PARAGRAPH_LINES_CONSECUTIVE).replaceFirst("(?s)^<p[^>]*>","").replaceFirst("(?s)</p>\\s*$","");
            int spanEnd=newline<0?end:end+1;boolean center=centered(text,start,spanEnd),indented=false;
            for(Indent margin:text.getSpans(start,spanEnd,Indent.class))if(text.getSpanStart(margin)<=start&&text.getSpanEnd(margin)>=spanEnd)indented=true;
            html.append("<p style=\"");if(center)html.append("text-align:center;");else if(indented)html.append("text-indent:2em;");html.append("\">").append(inline).append("</p>\n");
            if(newline<0)break;start=newline+1;
        }while(start<=text.length());
        return html.toString();
    }
    private ParagraphFormatting(){}
}
