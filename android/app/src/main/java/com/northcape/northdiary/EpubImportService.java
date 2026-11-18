package com.northcape.northdiary;

import android.content.ContentValues;
import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import android.text.*;
import android.text.style.URLSpan;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
import static com.northcape.northdiary.Models.*;

/** Validate without writes; merge in one transaction and roll back newly copied images. */
final class EpubImportService {
    private static final long TOTAL=200L*1024*1024,MEMBER=32L*1024*1024;
    static final class Asset {Attachment attachment;String caption;File source;}
    static final class Entry {JSONObject record;String target,html,text;List<Asset> assets=new ArrayList<>();}
    static final class Preview {
        File source,stage;final List<Entry> entries=new ArrayList<>();int fresh,conflicts,skipped;
        void close(boolean keepSource){if(stage!=null)ArchiveService.remove(stage);if(!keepSource&&source!=null)source.delete();}
        String summary(){return "新增 "+fresh+" 篇 · 冲突副本 "+conflicts+" 篇 · 跳过重复 "+skipped+" 篇";}
    }
    static final class Result {int imported,skipped,conflicts;}
    static Preview prepare(Context context,DiaryStore store,InputStream source)throws Exception{
        File file=File.createTempFile("epub-import-source-",".epub",context.getCacheDir());
        try{try(InputStream in=source;OutputStream out=new FileOutputStream(file)){DiaryStore.copy(in,out,220L*1024*1024);}return prepare(context,store,file);}catch(Exception e){file.delete();throw e;}
    }
    static Preview prepare(Context context,DiaryStore store,File source)throws Exception{
        File canonical=source.getCanonicalFile();ExchangeRecords.require(canonical.getParentFile().equals(context.getCacheDir().getCanonicalFile())&&canonical.getName().matches("epub-import-source-.*\\.epub"),"导入缓存无效");
        Preview preview=new Preview();preview.source=canonical;preview.stage=new File(context.getCacheDir(),"epub-import-stage-"+UUID.randomUUID());ExchangeRecords.require(preview.stage.mkdir(),"无法准备导入目录");
        try{
            try(ZipFile zip=new ZipFile(canonical)){
                ExchangeRecords.require(zip.size()<=5000,"EPUB 文件过多");long size=0;for(Enumeration<? extends ZipEntry> all=zip.entries();all.hasMoreElements();){ZipEntry item=all.nextElement();ExchangeRecords.require(item.getSize()>=0&&item.getSize()<=MEMBER,"EPUB 条目过大");size+=item.getSize();ExchangeRecords.require(size<=TOTAL,"EPUB 解压后超过 200 MiB");}
            }
            Map<String,File> images=new HashMap<>();Set<String> names=new HashSet<>();String manifest=null;long total=0;boolean mime=false;
            try(ZipInputStream zip=new ZipInputStream(new BufferedInputStream(new FileInputStream(canonical)))){
                ZipEntry entry;while((entry=zip.getNextEntry())!=null){
                    String path=entry.getName();ExchangeRecords.require(names.add(path)&&names.size()<=5000,"EPUB 文件重复或数量过多");
                    String name=entry.isDirectory()&&path.endsWith("/")?path.substring(0,path.length()-1):path;
                    ExchangeRecords.require(!name.isEmpty()&&!name.startsWith("/")&&!name.contains("\\")&&!name.contains(":")&&!Arrays.asList(name.split("/",-1)).stream().anyMatch(p->p.equals("..")||p.equals(".")||p.isEmpty()),"EPUB 包含不安全路径");
                    if(entry.isDirectory())continue;
                    long available=Math.min(MEMBER,TOTAL-total);ExchangeRecords.require(available>=0,"EPUB 解压后超过 200 MiB");
                    if(path.equals(ExchangeRecords.PATH)){byte[] bytes=DiaryStore.readBytes(zip,Math.min(8L*1024*1024,available));total+=bytes.length;manifest=StandardCharsets.UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(bytes)).toString();}
                    else if(path.equals("mimetype")){byte[] bytes=DiaryStore.readBytes(zip,64);total+=bytes.length;mime=Arrays.equals(bytes,"application/epub+zip".getBytes(StandardCharsets.US_ASCII));}
                    else if(path.matches("EPUB/images/image-[1-9][0-9]*\\.(png|jpg|gif)")){File image=new File(preview.stage,"image-"+images.size());try(OutputStream out=new FileOutputStream(image)){total+=DiaryStore.copy(zip,out,available);}images.put(path,image);}
                    else total+=DiaryStore.copy(zip,new OutputStream(){@Override public void write(int b){}@Override public void write(byte[] b,int off,int len){}},available);
                }
            }
            ExchangeRecords.require(mime,"不是有效的 EPUB 文件");ExchangeRecords.require(manifest!=null,"仅支持带 NorthDiary 数据清单的 EPUB。普通电子书及安卓 0.1.3 的阅读文集暂不能导入，请从新版重新导出。");
            JSONObject data=ExchangeRecords.parse(manifest);Object version=data.get("version");ExchangeRecords.require(data.getString("format").equals(ExchangeRecords.FORMAT)&&(version instanceof Integer||version instanceof Long)&&((Number)version).longValue()>=1&&((Number)version).longValue()<=4,"不支持此 NorthDiary EPUB 版本");
            JSONArray records=data.getJSONArray("articles");ExchangeRecords.require(records.length()>0&&records.length()<=1000,"文章数量无效或超过 1000 篇");Set<String> ids=new HashSet<>();Map<String,String> people=new HashMap<>(),codes=new HashMap<>();int references=0;
            for(int i=0;i<records.length();i++){
                JSONObject record=records.getJSONObject(i);ExchangeRecords.validate(record,data.getInt("version"));ExchangeRecords.require(ids.add(record.getString("id")),"同一文章重复出现");references+=record.getJSONArray("assets").length();ExchangeRecords.require(references<=5000,"图片引用过多");
                JSONArray persons=record.optJSONArray("people");if(persons!=null)for(int p=0;p<persons.length();p++){
                    JSONObject person=persons.getJSONObject(p);String id=person.getString("id"),profile=ExchangeRecords.canonical(person,false),code=person.getString("code");
                    ExchangeRecords.require(!people.containsKey(id)||people.get(id).equals(profile),"同一人物资料不一致");ExchangeRecords.require(!codes.containsKey(code)||codes.get(code).equals(id),"人物代号重复");people.put(id,profile);codes.put(code,id);
                }
                Entry prepared=prepareArticle(context,record,images);preview.entries.add(prepared);
            }
            synchronized(store){for(Entry entry:preview.entries){int status=status(store,entry);if(status==0)preview.fresh++;else if(status==1)preview.conflicts++;else preview.skipped++;}}return preview;
        }catch(Exception e){preview.close(false);if(e instanceof IOException)throw e;throw new IOException("EPUB 数据无效或已损坏："+e.getMessage(),e);}
    }
    private static Entry prepareArticle(Context context,JSONObject record,Map<String,File> files)throws Exception{
        Entry entry=new Entry();entry.record=record;entry.target=ExchangeRecords.stableId("northdiary-import:"+record.getString("id")+":"+ExchangeRecords.fingerprint(record));
        Map<String,Asset> byOriginalId=new HashMap<>();List<Attachment> originals=new ArrayList<>();JSONArray assets=record.getJSONArray("assets");
        for(int i=0;i<assets.length();i++){
            JSONObject nativeAsset=assets.getJSONObject(i);File file=files.get(nativeAsset.getString("archive_path"));ExchangeRecords.require(file!=null&&file.isFile(),"EPUB 缺少图片："+nativeAsset.getString("name"));
            String suffix=EpubService.imageType(file),mime=suffix.equals("jpg")?"image/jpeg":"image/"+suffix;
            ExchangeRecords.require(mime.equals(nativeAsset.getString("media_type"))&&ExchangeRecords.sha256(file).equals(nativeAsset.getString("sha256")),"图片校验失败");
            Attachment original=new Attachment();original.id=nativeAsset.getString("id");original.path=nativeAsset.getString("relative_path");original.name=nativeAsset.getString("name");original.mime=mime;originals.add(original);
            Asset asset=new Asset();asset.source=file;asset.caption=nativeAsset.getString("caption");asset.attachment=new Attachment();asset.attachment.id=UUID.randomUUID().toString();asset.attachment.name=original.name;asset.attachment.mime=mime;asset.attachment.path="attachments/"+asset.attachment.id+"."+suffix;entry.assets.add(asset);byOriginalId.put(original.id,asset);
        }
        SpannableStringBuilder body=new SpannableStringBuilder(ArticleText.parse(context,record.getString("body_html"),originals));Set<String> used=new HashSet<>();
        for(URLSpan link:body.getSpans(0,body.length(),URLSpan.class)){
            String url=link.getURL();int start=body.getSpanStart(link),end=body.getSpanEnd(link);body.removeSpan(link);
            if(url.startsWith("ndiary-image:")){String original=url.substring("ndiary-image:".length());Asset asset=byOriginalId.get(original);ExchangeRecords.require(asset!=null,"正文引用的图片未在清单中");used.add(original);body.setSpan(new ArticleText.ManagedLink("ndiary-image:"+asset.attachment.id),start,end,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);}
            else if(url.matches("(?is)https?://.*"))body.setSpan(new ArticleText.ManagedLink(url),start,end,Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
        }
        ExchangeRecords.require(used.equals(byOriginalId.keySet()),"图片清单与正文引用不一致");entry.html=ParagraphFormatting.html(body);entry.text=body.toString();return entry;
    }
    private static int status(DiaryStore store,Entry entry)throws Exception{
        if(!store.strings("SELECT id FROM articles WHERE id=?",entry.target).isEmpty())return 2;
        String original=entry.record.getString("id");if(store.strings("SELECT id FROM articles WHERE id=?",original).isEmpty())return 0;
        if(!store.get(original).deleted)try{
            JSONArray assets=new JSONArray();for(Attachment attachment:store.attachments(original)){
                JSONObject row=new JSONObject();row.put("id",attachment.id).put("relative_path",attachment.path).put("name",attachment.name).put("media_type",attachment.mime).put("sha256",ExchangeRecords.sha256(ArchiveService.attachmentFile(store.root,attachment.path)));
                row.put("caption",store.strings("SELECT caption FROM attachments WHERE id=?",attachment.id).get(0));assets.put(row);
            }
            if(ExchangeRecords.fingerprint(ExchangeRecords.article(store,original,assets)).equals(ExchangeRecords.fingerprint(entry.record)))return 2;
        }catch(Exception ignored){}return 1;
    }
    static Result apply(DiaryStore store,Preview preview)throws Exception{
        Result result=new Result();List<File> created=new ArrayList<>();
        synchronized(store){SQLiteDatabase db=store.getWritableDatabase();try{db.beginTransaction();try{
            long position=Long.parseLong(store.strings("SELECT COALESCE(MAX(sort_order),0) FROM articles").get(0));
            for(Entry entry:preview.entries){
                int status=status(store,entry);if(status==2){result.skipped++;continue;}JSONObject record=entry.record;ContentValues row=new ContentValues();
                row.put("id",entry.target);row.put("title",record.getString("title")+(status==1?"（导入副本）":""));row.put("diary_date",record.getString("diary_date"));row.put("body_html",entry.html);row.put("body_text",entry.text);row.put("created_at",record.getString("created_at"));row.put("updated_at",record.getString("updated_at"));row.put("pinned",record.getInt("pinned"));row.put("sort_order",++position);db.insertOrThrow("articles",null,row);
                if(record.optBoolean("outside_timeline",false))db.execSQL("INSERT INTO outside_articles VALUES (?)",new Object[]{entry.target});
                for(String kind:new String[]{"categories","tags"})for(String name:ExchangeRecords.labels(record.getJSONArray(kind),500,1000)){
                    ContentValues label=new ContentValues();label.put("id",UUID.randomUUID().toString());label.put("name",name);db.insertWithOnConflict(kind,null,label,SQLiteDatabase.CONFLICT_IGNORE);String key=store.strings("SELECT id FROM "+kind+" WHERE name=?",name).get(0);db.execSQL("INSERT INTO article_"+kind+" VALUES (?,?)",new Object[]{entry.target,key});
                }
                for(String name:ExchangeRecords.labels(record.getJSONArray("temporary_tags"),500,1000))db.execSQL("INSERT INTO article_temporary_tags VALUES (?,?)",new Object[]{entry.target,name});
                JSONArray people=record.optJSONArray("people");if(people!=null)for(int i=0;i<people.length();i++)db.execSQL("INSERT INTO article_people VALUES (?,?)",new Object[]{entry.target,importPerson(store,people.getJSONObject(i))});
                int order=0;for(Asset asset:entry.assets){
                    File destination=ArchiveService.attachmentFile(store.root,asset.attachment.path);ExchangeRecords.require(destination.createNewFile(),"图片文件已存在，未覆盖");created.add(destination);try(InputStream in=new FileInputStream(asset.source);OutputStream out=new FileOutputStream(destination)){DiaryStore.copy(in,out,MEMBER);}
                    ContentValues attachment=new ContentValues();attachment.put("id",asset.attachment.id);attachment.put("article_id",entry.target);attachment.put("name",asset.attachment.name);attachment.put("relative_path",asset.attachment.path);attachment.put("mime_type",asset.attachment.mime);attachment.put("caption",asset.caption);attachment.put("position",order++);db.insertOrThrow("attachments",null,attachment);
                }
                result.imported++;if(status==1)result.conflicts++;
            }
            db.setTransactionSuccessful();
        }finally{db.endTransaction();}}catch(Exception e){for(File file:created)file.delete();throw e;}}
        return result;
    }
    private static String importPerson(DiaryStore store,JSONObject person)throws Exception{
        String original=person.getString("id"),code=person.getString("code");boolean exists=!store.strings("SELECT id FROM people WHERE id=?",original).isEmpty();
        if(exists&&ExchangeRecords.canonical(ExchangeRecords.person(store,original),false).equals(ExchangeRecords.canonical(person,false)))return original;
        List<String> owner=store.strings("SELECT id FROM people WHERE code=?",code);String id=original;
        if(exists||!owner.isEmpty()){id=ExchangeRecords.stableId("northdiary-person:"+original+":"+ExchangeRecords.sha256(ExchangeRecords.canonical(person,true).getBytes(StandardCharsets.UTF_8)));if(!store.strings("SELECT id FROM people WHERE id=?",id).isEmpty())return id;}
        if(!owner.isEmpty()){String base=code.substring(0,Math.min(50,code.length())),suffix=id.replace("-","");code=base+"（导入-"+suffix+"）";int count=0;while(!store.strings("SELECT id FROM people WHERE code=?",code).isEmpty())code=base+"（导入-"+suffix+"-"+(++count)+"）";}
        ContentValues value=new ContentValues();value.put("id",id);value.put("code",code);for(String field:new String[]{"name","birth_date","met_date","met_how"})value.put(field,person.getString(field));value.put("pinned",person.getInt("pinned"));value.put("starred",person.getInt("starred"));store.getWritableDatabase().insertOrThrow("people",null,value);
        for(String key:new String[]{"relationships","temporary_relationships"}){
            JSONArray labels=person.optJSONArray(key);if(labels==null)continue;for(String name:ExchangeRecords.labels(labels,100,100)){
                if(key.equals("relationships"))store.getWritableDatabase().execSQL("INSERT OR IGNORE INTO relationship_tags VALUES (?)",new Object[]{name});
                store.getWritableDatabase().execSQL("INSERT INTO "+(key.equals("relationships")?"person_relationship_tags":"person_temporary_relationship_tags")+" VALUES (?,?)",new Object[]{id,name});
            }
        }
        return id;
    }
    private EpubImportService(){}
}
