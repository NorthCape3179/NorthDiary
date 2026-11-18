package com.northcape.northdiary;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;

/** Stages and validates complete backups before any active-store switch. */
final class ArchiveService {
    private static final long LIMIT=200L*1024*1024;
    static File attachmentFile(File root,String relative) throws IOException {
        if(!relative.matches("attachments/[A-Za-z0-9._-]+")) throw new IOException("附件路径无效");
        File path=new File(root,relative).getCanonicalFile();
        if(!path.getParentFile().equals(new File(root,"attachments").getCanonicalFile())) throw new IOException("附件路径越界");
        return path;
    }
    static File export(Context c,DiaryStore store) throws Exception {
        File snapshot=File.createTempFile("diary-snapshot-",".sqlite3",c.getCacheDir());
        File archive=File.createTempFile("NorthDiary-",".ndiary",c.getCacheDir());
        try {
            synchronized(store) {
                store.snapshot(snapshot);
                try(ZipOutputStream zip=new ZipOutputStream(new BufferedOutputStream(new FileOutputStream(archive)))) {
                    zip.putNextEntry(new ZipEntry("manifest.json"));
                    zip.write("{\"format\":\"NorthDiary\",\"version\":1}".getBytes(StandardCharsets.UTF_8)); zip.closeEntry();
                    long total=add(zip,snapshot,DiaryStore.DB,LIMIT);
                    try(SQLiteDatabase data=SQLiteDatabase.openDatabase(snapshot.getPath(),null,SQLiteDatabase.OPEN_READONLY);
                        Cursor paths=data.rawQuery("SELECT relative_path FROM attachments ORDER BY relative_path",null)) {
                        if(paths.getCount()>9998)throw new IOException("附件数量超过初版限制");
                        while(paths.moveToNext()) {
                            String path=paths.getString(0);File f=attachmentFile(store.root,path);
                            if(!f.isFile())throw new IOException("附件缺失，未导出不完整备份");
                            total+=add(zip,f,path,LIMIT-total);
                        }
                    }
                }
            }
            return archive;
        } catch(Exception e) { archive.delete(); throw e; }
        finally { snapshot.delete(); }
    }
    private static long add(ZipOutputStream zip,File f,String name,long available) throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        long length;
        try(InputStream in=new FileInputStream(f)) { length=DiaryStore.copy(in,zip,available); }
        zip.closeEntry(); return length;
    }
    static File stage(Context context,InputStream source) throws Exception {
        File stage=new File(context.getFilesDir(),"store-"+UUID.randomUUID());
        if(!new File(stage,"attachments").mkdirs()) throw new IOException("无法创建恢复目录");
        Set<String> names=new HashSet<>(); long total=0;
        try {
            try(ZipInputStream zip=new ZipInputStream(new BufferedInputStream(source))) {
                ZipEntry e;
                while((e=zip.getNextEntry())!=null) {
                    String name=e.getName();
                    if(!names.add(name)||names.size()>10000) throw new IOException("备份含重复项目或项目过多");
                    if(e.isDirectory()) { if(!name.equals("attachments/"))throw new IOException("备份目录无效"); continue; }
                    File file;
                    if(name.equals(DiaryStore.DB)||name.equals("manifest.json")) file=new File(stage,name);
                    else file=attachmentFile(stage,name);
                    try(OutputStream out=new FileOutputStream(file)) { total+=DiaryStore.copy(zip,out,LIMIT-total); }
                }
            }
            File manifest=new File(stage,"manifest.json");
            try(InputStream in=new FileInputStream(manifest)) {
                JSONObject j=new JSONObject(new String(DiaryStore.readBytes(in,8192),StandardCharsets.UTF_8));
                if(!j.getString("format").equals("NorthDiary")||j.getInt("version")!=1) throw new IOException("不支持此备份格式");
            }
            validate(stage); return stage;
        } catch(Exception e) { remove(stage); throw e; }
    }
    static void validate(File root) throws IOException {
        File file=new File(root,DiaryStore.DB);
        if(!file.isFile()) throw new IOException("备份缺少数据库");
        try(SQLiteDatabase db=SQLiteDatabase.openDatabase(file.getPath(),null,SQLiteDatabase.OPEN_READONLY)) {
            if(db.getVersion()!=7) throw new IOException("此初版仅支持 schema v7 的完整备份");
            try(Cursor c=db.rawQuery("PRAGMA integrity_check",null)) { if(!c.moveToFirst()||!"ok".equals(c.getString(0)))throw new IOException("数据库完整性检查失败"); }
            try(Cursor c=db.rawQuery("PRAGMA foreign_key_check",null)) { if(c.moveToFirst())throw new IOException("备份的关联记录不完整"); }
            try(Cursor c=db.rawQuery("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view')",null)) { if(c.moveToFirst())throw new IOException("备份含非标准数据库对象"); }
            String[] tables={"articles","categories","tags","article_categories","article_tags","attachments","article_temporary_tags","people","article_people","relationship_tags","person_relationship_tags","person_temporary_relationship_tags","outside_articles","draft_articles"};
            String[] columns={"id,title,diary_date,body_html,body_text,created_at,updated_at,deleted_at,pinned,sort_order","id,name,parent_id","id,name","article_id,category_id","article_id,tag_id","id,article_id,name,relative_path,mime_type,caption,position","article_id,name","id,name,code,birth_date,met_date,met_how,pinned,starred","article_id,person_id","name","person_id,name","person_id,name","article_id","article_id"};
            for(int i=0;i<tables.length;i++) try(Cursor c=db.rawQuery("SELECT * FROM "+tables[i]+" LIMIT 0",null)) {
                if(!Arrays.equals(c.getColumnNames(),columns[i].split(",")))throw new IOException("数据表结构不受支持："+tables[i]);
            }
            try(Cursor c=db.rawQuery("SELECT diary_date FROM articles WHERE id NOT IN (SELECT article_id FROM outside_articles)",null)) {
                while(c.moveToNext()) PartialDate.normalize(c.getString(0));
            }
            try(Cursor c=db.rawQuery("SELECT relative_path FROM attachments",null)) {
                while(c.moveToNext()) if(!attachmentFile(root,c.getString(0)).isFile())throw new IOException("备份缺少附件");
            }
        } catch(RuntimeException e) { throw new IOException("备份数据库无效："+e.getMessage(),e); }
    }
    static void remove(File file) { File[] files=file.listFiles(); if(files!=null)for(File child:files)remove(child); file.delete(); }
}
