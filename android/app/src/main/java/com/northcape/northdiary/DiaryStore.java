package com.northcape.northdiary;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.*;
import static com.northcape.northdiary.Models.*;

/** One transaction per edit; never replaces an article to update its relationships. */
final class DiaryStore extends SQLiteOpenHelper {
    static final String DB = "northdiary.sqlite3";
    final File root;
    private final Context context;
    DiaryStore(Context context, File root) {
        super(context, new File(root, DB).getAbsolutePath(), null, 7);
        this.context = context;
        this.root = root;
        if (!new File(root, "attachments").isDirectory() && !new File(root, "attachments").mkdirs())
            throw new IllegalStateException("无法创建附件目录");
        getWritableDatabase();
    }
    static File activeRoot(Context c) {
        return new File(c.getFilesDir(), c.getSharedPreferences("archive", 0).getString("active", "store-initial"));
    }
    @Override public void onConfigure(SQLiteDatabase db) { db.setForeignKeyConstraintsEnabled(true); }
    @Override public void onCreate(SQLiteDatabase db) {
        try (InputStream input = context.getAssets().open("schema.sql")) {
            String sql = new String(readBytes(input, 256 * 1024), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) if (!statement.trim().isEmpty()) db.execSQL(statement);
        } catch (IOException e) { throw new IllegalStateException("无法初始化数据库", e); }
    }
    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        throw new IllegalStateException("此初版只支持 schema v7，请先用桌面新版导出备份");
    }
    @Override public void onDowngrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        throw new IllegalStateException("此数据来自更新版本，请升级安卓端");
    }
    static String now() { return OffsetDateTime.now().toString(); }
    synchronized List<Article> list(String query, String tag, int space, boolean byDate, String person) {
        String sql = "SELECT a.* FROM articles a WHERE a.deleted_at IS " + (space == 3 ? "NOT NULL" : "NULL");
        List<String> args = new ArrayList<>();
        if (space != 3) {
            sql += (space == 2 ? " AND EXISTS" : " AND NOT EXISTS") + " (SELECT 1 FROM draft_articles d WHERE d.article_id=a.id)";
            if (space != 2) sql += (space == 1 ? " AND EXISTS" : " AND NOT EXISTS") + " (SELECT 1 FROM outside_articles o WHERE o.article_id=a.id)";
        }
        if (!query.isEmpty()) {
            sql += " AND (instr(lower(a.title),lower(?))>0 OR instr(lower(a.body_text),lower(?))>0)";
            args.add(query); args.add(query);
        }
        if (!tag.isEmpty()) {
            sql += " AND EXISTS (SELECT 1 FROM article_tags r JOIN tags t ON t.id=r.tag_id WHERE r.article_id=a.id AND t.name=?)";
            args.add(tag);
        }
        if (person != null) {
            sql += " AND EXISTS (SELECT 1 FROM article_people p WHERE p.article_id=a.id AND p.person_id=?)";
            args.add(person);
        }
        sql += " ORDER BY " + (byDate && space == 0 ? "replace(a.diary_date,'未知','00')" : "a.created_at") + " DESC,a.id";
        List<Article> results = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery(sql, args.toArray(new String[0]))) {
            while (c.moveToNext()) results.add(readArticle(c));
        }
        return results;
    }
    private static String value(Cursor c, String name) { return c.getString(c.getColumnIndexOrThrow(name)); }
    private static Article readArticle(Cursor c) {
        Article a = new Article();
        a.id = value(c,"id"); a.title = value(c,"title"); a.date = value(c,"diary_date");
        a.html = value(c,"body_html"); a.text = value(c,"body_text");
        a.created = value(c,"created_at"); a.updated = value(c,"updated_at"); a.deleted = value(c,"deleted_at") != null;
        return a;
    }
    synchronized Article get(String id) {
        Article a;
        try (Cursor c = getReadableDatabase().rawQuery("SELECT * FROM articles WHERE id=?", new String[]{id})) {
            if (!c.moveToFirst()) throw new IllegalArgumentException("文章不存在");
            a = readArticle(c);
        }
        a.outside = exists("outside_articles", id); a.draft = exists("draft_articles", id);
        a.tags = strings("SELECT t.name FROM tags t JOIN article_tags r ON r.tag_id=t.id WHERE r.article_id=? ORDER BY t.name",id);
        a.people = strings("SELECT person_id FROM article_people WHERE article_id=?",id);
        return a;
    }
    private boolean exists(String table, String id) {
        try (Cursor c = getReadableDatabase().rawQuery("SELECT 1 FROM " + table + " WHERE article_id=?",new String[]{id})) { return c.moveToFirst(); }
    }
    synchronized List<String> strings(String sql, String... args) {
        List<String> result = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery(sql,args)) { while(c.moveToNext()) result.add(c.getString(0)); }
        return result;
    }
    synchronized void save(Article a) {
        if (!a.outside) a.date = PartialDate.normalize(a.date);
        SQLiteDatabase db = getWritableDatabase();
        String originalCreated = a.created;
        db.beginTransaction();
        try {
            ContentValues v = new ContentValues();
            v.put("title", a.title.trim().isEmpty() ? "未命名文章" : a.title.trim());
            v.put("diary_date", a.date); v.put("body_html",a.html); v.put("body_text",a.text);
            String stamp = now(); v.put("updated_at",stamp);
            if (a.created.isEmpty()) {
                a.created = stamp; v.put("id",a.id); v.put("created_at",a.created);
                db.insertOrThrow("articles",null,v);
            } else if (db.update("articles",v,"id=? AND deleted_at IS NULL",new String[]{a.id}) != 1)
                throw new IllegalStateException("文章已删除，编辑内容仍保留在草稿");
            db.delete("article_tags","article_id=?",new String[]{a.id});
            for (String name : new LinkedHashSet<>(a.tags)) {
                name = name.trim(); if (name.isEmpty()) continue;
                ContentValues t = new ContentValues(); t.put("id",UUID.randomUUID().toString()); t.put("name",name);
                db.insertWithOnConflict("tags",null,t,SQLiteDatabase.CONFLICT_IGNORE);
                String key = strings("SELECT id FROM tags WHERE name=?",name).get(0);
                db.execSQL("INSERT INTO article_tags VALUES (?,?)",new Object[]{a.id,key});
            }
            db.delete("article_people","article_id=?",new String[]{a.id});
            for (String id : new LinkedHashSet<>(a.people)) db.execSQL("INSERT INTO article_people VALUES (?,?)",new Object[]{a.id,id});
            membership(db,"outside_articles",a.id,a.outside); membership(db,"draft_articles",a.id,a.draft);
            db.setTransactionSuccessful();
        } catch (RuntimeException e) {
            // The caller keeps its draft. A failed first insert must remain an insert on retry.
            a.created = originalCreated;
            throw e;
        } finally { db.endTransaction(); }
    }
    private static void membership(SQLiteDatabase db,String table,String id,boolean enabled) {
        db.delete(table,"article_id=?",new String[]{id});
        if (enabled) db.execSQL("INSERT INTO " + table + " VALUES (?)",new Object[]{id});
    }
    synchronized void deleted(String id, boolean deleted) {
        ContentValues v = new ContentValues(); if (deleted) v.put("deleted_at",now()); else v.putNull("deleted_at");
        v.put("updated_at",now()); getWritableDatabase().update("articles",v,"id=?",new String[]{id});
    }
    synchronized List<Person> people(String query) {
        List<Person> list = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery("SELECT * FROM people WHERE instr(lower(name),lower(?))>0 OR instr(lower(code),lower(?))>0 ORDER BY name,id", new String[]{query,query})) {
            while(c.moveToNext()) {
                Person p = new Person(); p.id=value(c,"id"); p.name=value(c,"name"); p.code=value(c,"code");
                p.birth=value(c,"birth_date"); p.met=value(c,"met_date"); p.how=value(c,"met_how"); list.add(p);
            }
        }
        return list;
    }
    synchronized void savePerson(Person p) {
        if (p.name.trim().isEmpty() || p.code.trim().isEmpty()) throw new IllegalArgumentException("姓名和代号不能为空");
        if (!p.birth.isEmpty()) p.birth=PartialDate.normalize(p.birth);
        if (!p.met.isEmpty()) p.met=PartialDate.normalize(p.met);
        ContentValues v=new ContentValues(); v.put("name",p.name.trim()); v.put("code",p.code.trim());
        v.put("birth_date",p.birth); v.put("met_date",p.met); v.put("met_how",p.how);
        SQLiteDatabase db=getWritableDatabase();
        if (db.update("people",v,"id=?",new String[]{p.id}) == 0) { v.put("id",p.id); db.insertOrThrow("people",null,v); }
    }
    synchronized void deletePerson(String id) { getWritableDatabase().delete("people","id=?",new String[]{id}); }
    synchronized List<Attachment> attachments(String article) {
        List<Attachment> list=new ArrayList<>();
        try (Cursor c=getReadableDatabase().rawQuery("SELECT * FROM attachments WHERE article_id=? ORDER BY position,id",new String[]{article})) {
            while(c.moveToNext()) { Attachment a=new Attachment(); a.id=value(c,"id"); a.name=value(c,"name"); a.path=value(c,"relative_path"); a.mime=value(c,"mime_type"); list.add(a); }
        } return list;
    }
    synchronized void addAttachment(String article, Attachment a) {
        ContentValues v=new ContentValues(); v.put("id",a.id); v.put("article_id",article); v.put("name",a.name);
        v.put("relative_path",a.path); v.put("mime_type",a.mime);
        getWritableDatabase().insertOrThrow("attachments",null,v);
    }
    synchronized void snapshot(File destination) throws IOException {
        // Logical snapshot inside one source transaction, independent of WAL and Activity instances.
        SQLiteDatabase source=getReadableDatabase();source.beginTransaction();
        try(SQLiteDatabase target=SQLiteDatabase.openOrCreateDatabase(destination,null)) {
            target.beginTransaction();
            try {
                List<String> names=new ArrayList<>();
                try(Cursor tables=source.rawQuery("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name!='android_metadata'",null)) {
                    while(tables.moveToNext()){names.add(tables.getString(0));target.execSQL(tables.getString(1));}
                }
                for(String table:names)try(Cursor rows=source.rawQuery("SELECT * FROM \""+table.replace("\"","\"\"")+"\"",null)) {
                    while(rows.moveToNext()) {
                        ContentValues row=new ContentValues();
                        for(int i=0;i<rows.getColumnCount();i++) {
                            String name=rows.getColumnName(i);
                            switch(rows.getType(i)) {
                                case Cursor.FIELD_TYPE_NULL:row.putNull(name);break;
                                case Cursor.FIELD_TYPE_INTEGER:row.put(name,rows.getLong(i));break;
                                case Cursor.FIELD_TYPE_FLOAT:row.put(name,rows.getDouble(i));break;
                                case Cursor.FIELD_TYPE_BLOB:row.put(name,rows.getBlob(i));break;
                                default:row.put(name,rows.getString(i));
                            }
                        }
                        target.insertOrThrow(table,null,row);
                    }
                }
                try(Cursor indexes=source.rawQuery("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL",null)) {while(indexes.moveToNext())target.execSQL(indexes.getString(0));}
                target.setVersion(source.getVersion());target.setTransactionSuccessful();
            }finally{target.endTransaction();}
            source.setTransactionSuccessful();
        }catch(RuntimeException e){throw new IOException("无法创建一致的数据库快照",e);}
        finally{source.endTransaction();}
    }
    static byte[] readBytes(InputStream in,long limit) throws IOException { ByteArrayOutputStream out=new ByteArrayOutputStream(); copy(in,out,limit); return out.toByteArray(); }
    static long copy(InputStream in,OutputStream out,long limit) throws IOException {
        long count=0; byte[] buf=new byte[8192]; int n;
        while((n=in.read(buf))!=-1) { count+=n; if(count>limit) throw new IOException("文件超过此初版的大小限制"); out.write(buf,0,n); } return count;
    }
}
