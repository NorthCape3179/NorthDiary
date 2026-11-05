package com.northcape.northdiary;

import android.content.*;
import android.net.Uri;
import android.text.*;
import android.text.style.URLSpan;
import android.view.View;
import android.widget.Toast;
import java.util.List;
import java.util.regex.*;
import static com.northcape.northdiary.Models.*;

/** Native styled text, with managed image links. No WebView or remote image loading. */
final class ArticleText {
    static Spanned parse(Context c,String html,List<Attachment> attachments) {
        Matcher img=Pattern.compile("<img\\b[^>]*>",Pattern.CASE_INSENSITIVE).matcher(html);
        StringBuffer result=new StringBuffer();
        while(img.find()) {
            String replacement="[图片未关联]";
            for(Attachment a:attachments) if(img.group().contains(a.path)||img.group().contains(a.id)) {
                replacement="<a href=\"ndiary-image:"+a.id+"\">"+TextUtils.htmlEncode(a.name)+"</a>"; break;
            }
            img.appendReplacement(result,Matcher.quoteReplacement(replacement));
        }
        img.appendTail(result);
        SpannableStringBuilder text=ParagraphFormatting.parse(c,result.toString());
        for(URLSpan span:text.getSpans(0,text.length(),URLSpan.class)) {
            int start=text.getSpanStart(span),end=text.getSpanEnd(span);text.removeSpan(span);
            text.setSpan(new ManagedLink(span.getURL()),start,end,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        return text;
    }
    static void open(Context c,String url) {
        try {
            Intent intent=new Intent(Intent.ACTION_VIEW);
            if(url.startsWith("ndiary-image:")) {
                String id=url.substring("ndiary-image:".length());
                Uri uri=Uri.parse("content://"+c.getPackageName()+".attachments/"+id);
                intent.setDataAndType(uri,c.getContentResolver().getType(uri));
                intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } else {
                Uri uri=Uri.parse(url);String scheme=uri.getScheme();
                if(!"https".equalsIgnoreCase(scheme)&&!"http".equalsIgnoreCase(scheme)) throw new IllegalArgumentException("不支持此链接");
                intent.setData(uri);
            }
            c.startActivity(intent);
        }catch(Exception e){Toast.makeText(c,"无法打开链接：请确认文件存在且已安装查看器",Toast.LENGTH_LONG).show();}
    }
    static final class ManagedLink extends URLSpan {
        ManagedLink(String url){super(url);}
        @Override public void onClick(View v){open(v.getContext(),getURL());}
    }
}
