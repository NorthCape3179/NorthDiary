package com.northcape.northdiary;

import android.test.AndroidTestCase;
import android.text.*;
import android.text.style.*;
import android.graphics.Typeface;
import java.util.Collections;

public class ParagraphFormattingTest extends AndroidTestCase {
    public void testIndentCenterRichTextAndLinksRoundTrip(){
        String original="标题\n这一段正文\n图片链接\n";SpannableStringBuilder text=new SpannableStringBuilder(original);
        text.setSpan(new StyleSpan(Typeface.BOLD),3,5,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        int link=original.indexOf("图片链接");text.setSpan(new ArticleText.ManagedLink("https://example.invalid/memory"),link,link+4,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        ParagraphFormatting.autoIndent(text,true,ParagraphFormatting.indentWidth(getContext()));
        ParagraphFormatting.toggleCenter(text,0,2,true,ParagraphFormatting.indentWidth(getContext()));
        String html=ParagraphFormatting.html(text);assertTrue(html.contains("text-align:center"));assertTrue(html.contains("text-indent:2em"));
        for(int i=0;i<4;i++){
            text=new SpannableStringBuilder(ArticleText.parse(getContext(),html,Collections.emptyList()));assertEquals(original,text.toString());
            assertTrue(text.getSpans(0,text.length(),AlignmentSpan.class).length>0);assertTrue(text.getSpans(0,text.length(),StyleSpan.class).length>0);assertEquals(1,text.getSpans(0,text.length(),URLSpan.class).length);
            html=ParagraphFormatting.html(text);
        }
    }
    public void testNewParagraphAutoIndentAndDisableKeepsText(){
        SpannableStringBuilder text=new SpannableStringBuilder("第一段");ParagraphFormatting.autoIndent(text,true,34);text.append("\n第二段");ParagraphFormatting.autoIndent(text,true,34);
        assertEquals(2,text.getSpans(0,text.length(),ParagraphFormatting.Indent.class).length);
        ParagraphFormatting.autoIndent(text,false,34);assertEquals(0,text.getSpans(0,text.length(),ParagraphFormatting.Indent.class).length);assertEquals("第一段\n第二段",text.toString());
    }
}
