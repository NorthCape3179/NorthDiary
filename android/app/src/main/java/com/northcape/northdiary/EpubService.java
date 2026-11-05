package com.northcape.northdiary;

import android.content.Context;
import android.graphics.Typeface;
import android.text.*;
import android.text.style.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.zip.*;
import static com.northcape.northdiary.Models.*;

/** Reading EPUB 3: rebuild XHTML from native spans, never package unchecked source HTML. */
final class EpubService {
    private static final long LIMIT=200L*1024*1024;
    private static final String XHTML="http://www.w3.org/1999/xhtml";
    private static final class Image {
        Attachment attachment;File file;String href,mime;
    }
    static File export(Context context,DiaryStore store,List<String> ids,String title,String author)throws Exception {
        if(title.trim().isEmpty()||ids.isEmpty())throw new IOException("请填写书名，并至少选择一篇文章");
        if(ids.size()>1000||new HashSet<>(ids).size()!=ids.size())throw new IOException("每次最多导出 1000 篇，且不能重复选择文章");
        File output=File.createTempFile("NorthDiary-reading-",".epub",context.getCacheDir());
        try {
            synchronized(store){
                List<Article> articles=new ArrayList<>();Map<String,List<Attachment>> attachments=new HashMap<>();Map<String,Image> images=new LinkedHashMap<>();
                long total=0;
                for(String id:ids){
                    Article a=store.get(id);if(a.deleted||a.draft)throw new IOException("只能导出已确认且未删除的文章");articles.add(a);
                    if(a.html.length()>8*1024*1024)throw new IOException("单篇正文过长，请拆分文集");
                    total+=(long)a.html.length()*3;if(total>LIMIT)throw new IOException("文集超过 200 MiB 限制");
                    List<Attachment> files=store.attachments(id);attachments.put(id,files);
                    for(Attachment attachment:files){
                        if(images.containsKey(attachment.id))continue;
                        Image image=new Image();image.attachment=attachment;image.file=ArchiveService.attachmentFile(store.root,attachment.path);
                        if(!image.file.isFile())throw new IOException("附件缺失："+attachment.name);
                        String suffix=imageType(image.file);image.mime=suffix.equals("jpg")?"image/jpeg":"image/"+suffix;
                        image.href="images/image-"+(images.size()+1)+"."+suffix;images.put(attachment.id,image);
                        if(image.file.length()>32L*1024*1024)throw new IOException("图片超过 32 MiB："+attachment.name);
                        total+=image.file.length();if(total>LIMIT)throw new IOException("文集超过 200 MiB 限制");
                    }
                }
                try(ZipOutputStream zip=new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(output)))){
                    byte[] mime="application/epub+zip".getBytes(StandardCharsets.US_ASCII);CRC32 crc=new CRC32();crc.update(mime);
                    ZipEntry entry=new ZipEntry("mimetype");entry.setMethod(ZipEntry.STORED);entry.setSize(mime.length);entry.setCompressedSize(mime.length);entry.setCrc(crc.getValue());zip.putNextEntry(entry);zip.write(mime);zip.closeEntry();
                    text(zip,"META-INF/container.xml","<?xml version=\"1.0\" encoding=\"UTF-8\"?><container version=\"1.0\" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\"><rootfiles><rootfile full-path=\"EPUB/content.opf\" media-type=\"application/oebps-package+xml\"/></rootfiles></container>");
                    text(zip,"EPUB/style.css","body{line-height:1.7;margin:1em;}p{margin:0 0 .8em;white-space:pre-wrap;}h1{font-size:1.6em;}a{overflow-wrap:anywhere;}.date{color:#777;font-size:.9em;}");
                    StringBuilder manifest=new StringBuilder("<item id=\"nav\" href=\"nav.xhtml\" media-type=\"application/xhtml+xml\" properties=\"nav\"/><item id=\"css\" href=\"style.css\" media-type=\"text/css\"/>"),spine=new StringBuilder(),toc=new StringBuilder();
                    int index=0;JSONArray records=new JSONArray();int references=0;
                    for(Article a:articles){
                        index++;String path="text/chapter-"+index+".xhtml";
                        manifest.append("<item id=\"c").append(index).append("\" href=\"").append(path).append("\" media-type=\"application/xhtml+xml\"/>");spine.append("<itemref idref=\"c").append(index).append("\"/>");
                        toc.append("<li><a href=\"").append(path).append("\">").append(xml(a.title)).append("</a></li>");
                        StringBuilder content=new StringBuilder("<h1>").append(xml(a.title)).append("</h1>");
                        if(!a.outside)content.append("<p class=\"date\">").append(xml(PartialDate.label(a.date))).append("</p>");
                        Spanned parsed=ArticleText.parse(context,a.html.isEmpty()?"<p>"+xml(a.text)+"</p>":a.html,attachments.get(a.id));
                        JSONArray nativeAssets=new JSONArray();Set<String> linked=new HashSet<>();for(URLSpan link:parsed.getSpans(0,parsed.length(),URLSpan.class))if(link.getURL().startsWith("ndiary-image:"))linked.add(link.getURL().substring("ndiary-image:".length()));
                        String nativeHtml=a.html.isEmpty()?"<p>"+xml(a.text)+"</p>":a.html;
                        for(Attachment file:attachments.get(a.id)){
                            Image image=images.get(file.id);JSONObject asset=new JSONObject();asset.put("id",file.id).put("name",file.name).put("relative_path",file.path).put("archive_path","EPUB/"+image.href).put("media_type",image.mime).put("sha256",ExchangeRecords.sha256(image.file));
                            asset.put("caption",store.strings("SELECT caption FROM attachments WHERE id=?",file.id).get(0));nativeAssets.put(asset);references++;if(!linked.contains(file.id))nativeHtml+="<p><a href=\"ndiary-image:"+file.id+"\">"+xml(file.name)+"</a></p>";
                        }
                        JSONObject record=ExchangeRecords.article(store,a.id,nativeAssets);record.put("body_html",nativeHtml);ExchangeRecords.validate(record,4);records.put(record);
                        content.append(body(parsed,images));
                        if(!attachments.get(a.id).isEmpty()){
                            content.append("<section><h2>附件链接</h2><ul>");
                            for(Attachment file:attachments.get(a.id))content.append("<li><a href=\"../").append(images.get(file.id).href).append("\">").append(xml(file.name)).append("</a></li>");content.append("</ul></section>");
                        }
                        text(zip,"EPUB/"+path,page(a.title,"../style.css",content.toString()));
                    }
                    text(zip,"EPUB/nav.xhtml",page(title,"style.css","<nav epub:type=\"toc\" id=\"toc\"><h1>"+xml(title)+"</h1><ol>"+toc+"</ol></nav>"));
                    String exchange=new JSONObject().put("format",ExchangeRecords.FORMAT).put("version",4).put("articles",records).toString();if(exchange.getBytes(StandardCharsets.UTF_8).length>8*1024*1024||references>5000)throw new IOException("交换清单过大，请分批导出");
                    text(zip,ExchangeRecords.PATH,exchange);manifest.append("<item id=\"northdiary-data\" href=\"northdiary/manifest.json\" media-type=\"application/json\"/>");
                    index=0;for(Image image:images.values()){
                        manifest.append("<item id=\"image").append(++index).append("\" href=\"").append(image.href).append("\" media-type=\"").append(image.mime).append("\"/>");
                        zip.putNextEntry(new ZipEntry("EPUB/"+image.href));try(InputStream in=new FileInputStream(image.file)){DiaryStore.copy(in,zip,32L*1024*1024);}zip.closeEntry();
                    }
                    String metadata="<dc:identifier id=\"bookid\">urn:uuid:"+UUID.randomUUID()+"</dc:identifier><dc:title>"+xml(title)+"</dc:title><dc:language>zh-CN</dc:language>"+(author.trim().isEmpty()?"":"<dc:creator>"+xml(author)+"</dc:creator>")+"<meta property=\"dcterms:modified\">"+Instant.now().truncatedTo(ChronoUnit.SECONDS)+"</meta>";
                    text(zip,"EPUB/content.opf","<?xml version=\"1.0\" encoding=\"UTF-8\"?><package xmlns=\"http://www.idpf.org/2007/opf\" version=\"3.0\" unique-identifier=\"bookid\"><metadata xmlns:dc=\"http://purl.org/dc/elements/1.1/\">"+metadata+"</metadata><manifest>"+manifest+"</manifest><spine>"+spine+"</spine></package>");
                }
            }
            return output;
        }catch(Exception e){output.delete();throw e;}
    }
    static String imageType(File file)throws IOException {
        byte[] head=new byte[12];int length;try(InputStream in=new FileInputStream(file)){length=in.read(head);}
        if(length>=8&&head[0]==(byte)137&&head[1]==80&&head[2]==78&&head[3]==71&&head[4]==13&&head[5]==10&&head[6]==26&&head[7]==10)return "png";
        if(length>=3&&head[0]==(byte)255&&head[1]==(byte)216&&head[2]==(byte)255)return "jpg";
        if(length>=6&&(new String(head,0,6,StandardCharsets.US_ASCII).equals("GIF87a")||new String(head,0,6,StandardCharsets.US_ASCII).equals("GIF89a")))return "gif";
        throw new IOException("阅读文集目前仅支持 PNG、JPEG、GIF 图片，请先转换此附件："+file.getName());
    }
    private static String body(Spanned text,Map<String,Image> images)throws IOException {
        StringBuilder out=new StringBuilder();int start=0;
        do{
            int newline=text.toString().indexOf('\n',start),end=newline<0?text.length():newline,spanEnd=newline<0?end:end+1;
            boolean center=false,indent=false;
            for(AlignmentSpan s:text.getSpans(start,spanEnd,AlignmentSpan.class))if(s.getAlignment()==Layout.Alignment.ALIGN_CENTER)center=true;
            for(ParagraphFormatting.Indent s:text.getSpans(start,spanEnd,ParagraphFormatting.Indent.class))indent=true;
            out.append("<p").append(center?" style=\"text-align:center\"":indent?" style=\"text-indent:2em\"":"").append(">");
            if(start==end)out.append("<br/>");
            int at=start;
            while(at<end){
                int next=text.nextSpanTransition(at,end,CharacterStyle.class);boolean bold=false,italic=false;
                for(StyleSpan style:text.getSpans(at,next,StyleSpan.class)){bold|=(style.getStyle()&Typeface.BOLD)!=0;italic|=(style.getStyle()&Typeface.ITALIC)!=0;}
                String href=null;for(URLSpan link:text.getSpans(at,next,URLSpan.class)){
                    String url=link.getURL();
                    if(url.startsWith("ndiary-image:")){Image image=images.get(url.substring("ndiary-image:".length()));if(image==null)throw new IOException("正文引用的附件缺失");href="../"+image.href;}
                    else if(url.matches("(?is)https?://.*"))href=url;
                    break;
                }
                if(href!=null)out.append("<a href=\"").append(xml(href)).append("\">");if(bold)out.append("<strong>");if(italic)out.append("<em>");
                out.append(xml(text.subSequence(at,next).toString()));
                if(italic)out.append("</em>");if(bold)out.append("</strong>");if(href!=null)out.append("</a>");at=next;
            }
            out.append("</p>");if(newline<0)break;start=newline+1;
        }while(start<=text.length());return out.toString();
    }
    private static String page(String title,String css,String content){return "<?xml version=\"1.0\" encoding=\"UTF-8\"?><html xmlns=\""+XHTML+"\" xmlns:epub=\"http://www.idpf.org/2007/ops\" lang=\"zh-CN\" xml:lang=\"zh-CN\"><head><title>"+xml(title)+"</title><link rel=\"stylesheet\" type=\"text/css\" href=\""+css+"\"/></head><body>"+content+"</body></html>";}
    static String xml(String value){
        StringBuilder out=new StringBuilder();for(int at=0;at<value.length();){int c=value.codePointAt(at);at+=Character.charCount(c);if(c!=9&&c!=10&&c!=13&&(c<32||c>=0xD800&&c<=0xDFFF||c==0xFFFE||c==0xFFFF))continue;
            if(c=='&')out.append("&amp;");else if(c=='<')out.append("&lt;");else if(c=='>')out.append("&gt;");else if(c=='\"')out.append("&quot;");else if(c=='\'')out.append("&apos;");else out.appendCodePoint(c);
        }return out.toString();
    }
    private static void text(ZipOutputStream zip,String path,String text)throws IOException {zip.putNextEntry(new ZipEntry(path));zip.write(text.getBytes(StandardCharsets.UTF_8));zip.closeEntry();}
    private EpubService(){}
}
