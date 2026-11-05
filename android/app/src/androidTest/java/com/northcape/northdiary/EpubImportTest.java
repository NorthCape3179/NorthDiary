package com.northcape.northdiary;

import android.content.Context;
import android.content.ContentValues;
import android.net.Uri;
import android.os.Build;
import android.provider.MediaStore;
import android.database.sqlite.SQLiteException;
import android.test.AndroidTestCase;
import android.util.Base64;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
import static com.northcape.northdiary.Models.*;

public class EpubImportTest extends AndroidTestCase {
    private File root;private DiaryStore store;private byte[] fixture;private JSONObject expected;
    @Override protected void setUp()throws Exception{
        super.setUp();root=new File(getContext().getCacheDir(),"epub-import-test-"+UUID.randomUUID());store=new DiaryStore(getContext(),root);
        Context test=getContext().createPackageContext("com.northcape.northdiary.test",0);
        try(InputStream in=test.getAssets().open("desktop-v4.epub.base64")){fixture=Base64.decode(DiaryStore.readBytes(in,128*1024),Base64.DEFAULT);}
        try(InputStream in=test.getAssets().open("desktop-v4.expected.json")){expected=new JSONObject(new String(DiaryStore.readBytes(in,8192),StandardCharsets.UTF_8));}
    }
    @Override protected void tearDown()throws Exception{store.close();ArchiveService.remove(root);super.tearDown();}
    private EpubImportService.Preview preview()throws Exception{return EpubImportService.prepare(getContext(),store,new ByteArrayInputStream(fixture));}
    public void testDesktopFixturePreviewApplyAndIdempotentAfterLocalEditOrTrash()throws Exception{
        String first=expected.getJSONArray("articles").getJSONObject(0).getString("target");
        EpubImportService.Preview preview=preview();
        try{
            assertEquals(2,preview.fresh);assertEquals(0,store.exportable().size());
            for(int i=0;i<2;i++){JSONObject want=expected.getJSONArray("articles").getJSONObject(i);assertEquals(want.getString("target"),preview.entries.get(i).target);assertEquals(want.getString("fingerprint"),ExchangeRecords.fingerprint(preview.entries.get(i).record));}
            EpubImportService.Result result=EpubImportService.apply(store,preview);assertEquals(2,result.imported);assertEquals(0,result.skipped);
            Article a=store.get(first);assertTrue(a.categories.contains("校园"));assertTrue(a.tags.contains("回忆"));assertTrue(store.articleTags(first).contains("临时标签"));assertEquals("2026-未知-未知",a.date);assertEquals(expected.getString("person"),a.people.get(0));
            Attachment image=store.attachments(first).get(0);assertTrue(ArchiveService.attachmentFile(root,image.path).isFile());assertTrue(a.html.contains("ndiary-image:"+image.id));assertFalse(a.html.contains("<img"));assertTrue(a.html.contains("text-align:center"));
            assertEquals("1",store.strings("SELECT pinned FROM articles WHERE id=?",first).get(0));
            a.title="本机后续修改";store.save(a);store.deleted(first,true);
        }finally{preview.close(false);}
        EpubImportService.Preview again=preview();try{assertEquals(2,again.skipped);assertEquals(0,EpubImportService.apply(store,again).imported);assertEquals("本机后续修改",store.get(first).title);assertTrue(store.get(first).deleted);}finally{again.close(false);}
    }
    public void testArticleAndPersonConflictsNeverOverwriteAndReuseStableCopies()throws Exception{
        String sourceId=expected.getJSONArray("articles").getJSONObject(0).getString("id");Article local=new Article();local.id=sourceId;local.title="本地文章";local.date="2026";local.html="<p>保留</p>";local.text="保留";store.save(local);
        Person person=new Person();person.id=expected.getString("person");person.name="本地人物";person.code="QA-CLASSMATE";store.savePerson(person);
        EpubImportService.Preview preview=preview();try{
            assertEquals(1,preview.conflicts);assertEquals(1,preview.fresh);EpubImportService.Result result=EpubImportService.apply(store,preview);assertEquals(1,result.conflicts);assertEquals(2,result.imported);
            assertEquals("本地文章",store.get(sourceId).title);assertEquals("本地人物",store.strings("SELECT name FROM people WHERE id=?",person.id).get(0));
            String copy=expected.getString("person_copy");assertEquals("测试同学",store.strings("SELECT name FROM people WHERE id=? AND pinned=1 AND starred=1",copy).get(0));assertEquals("同学",store.strings("SELECT name FROM person_relationship_tags WHERE person_id=?",copy).get(0));
            assertEquals(2,store.people("").size());
        }finally{preview.close(false);}
        EpubImportService.Preview again=preview();try{assertEquals(2,EpubImportService.apply(store,again).skipped);assertEquals(2,store.people("").size());}finally{again.close(false);}
    }
    public void testRollbackRemovesCopiedFilesAndCanRetry()throws Exception{
        EpubImportService.Preview preview=preview();try{
            store.getWritableDatabase().execSQL("CREATE TRIGGER reject_second BEFORE INSERT ON articles WHEN NEW.title LIKE '时间线之外%' BEGIN SELECT RAISE(ABORT,'test failure'); END");
            try{EpubImportService.apply(store,preview);fail("second article must fail");}catch(SQLiteException expected){}
            assertEquals(0,store.exportable().size());assertEquals(0,store.people("").size());assertEquals(0,new File(root,"attachments").list().length);
            store.getWritableDatabase().execSQL("DROP TRIGGER reject_second");assertEquals(2,EpubImportService.apply(store,preview).imported);
        }finally{preview.close(false);}
    }
    private byte[] rewrite(boolean missingImage,boolean wrongHash,boolean traversal)throws Exception{
        ByteArrayOutputStream output=new ByteArrayOutputStream();
        try(ZipInputStream in=new ZipInputStream(new ByteArrayInputStream(fixture));ZipOutputStream out=new ZipOutputStream(output)){
            ZipEntry e;while((e=in.getNextEntry())!=null){byte[] data=DiaryStore.readBytes(in,16*1024*1024);if(missingImage&&e.getName().startsWith("EPUB/images/"))continue;
                if(wrongHash&&e.getName().equals(ExchangeRecords.PATH)){JSONObject json=new JSONObject(new String(data,StandardCharsets.UTF_8));json.getJSONArray("articles").getJSONObject(0).getJSONArray("assets").getJSONObject(0).put("sha256",String.join("",Collections.nCopies(64,"0")));data=json.toString().getBytes(StandardCharsets.UTF_8);}
                out.putNextEntry(new ZipEntry(e.getName()));out.write(data);out.closeEntry();
            }
            if(traversal){out.putNextEntry(new ZipEntry("../escape"));out.write(1);out.closeEntry();}
        }return output.toByteArray();
    }
    public void testDamagedMissingUnsafeAndDuplicateDataRejectedWithoutWrites()throws Exception{
        for(byte[] bad:Arrays.asList(rewrite(true,false,false),rewrite(false,true,false),rewrite(false,false,true),Arrays.copyOf(fixture,fixture.length-30))){
            try{EpubImportService.prepare(getContext(),store,new ByteArrayInputStream(bad));fail("bad package accepted");}catch(IOException expected){}
            assertEquals(0,store.exportable().size());assertEquals(0,new File(root,"attachments").list().length);
        }
        try{ExchangeRecords.parse("{\"version\":4,\"version\":3}");fail();}catch(IOException expected){}
    }
    public void testAndroidExportRoundTripAndKeepBookForDesktopValidation()throws Exception{
        EpubImportService.Preview desktop=preview();try{EpubImportService.apply(store,desktop);}finally{desktop.close(false);}
        List<String> ids=new ArrayList<>();for(Article a:store.exportable())ids.add(a.id);
        File book=EpubService.export(getContext(),store,ids,"安卓往返测试文集","NorthDiary QA"),otherRoot=new File(root,"other");
        try(DiaryStore other=new DiaryStore(getContext(),otherRoot);InputStream in=new FileInputStream(book)){
            EpubImportService.Preview mobile=EpubImportService.prepare(getContext(),other,in);try{assertEquals(2,mobile.fresh);assertEquals(2,EpubImportService.apply(other,mobile).imported);assertEquals(2,other.exportable().size());}finally{mobile.close(false);}
            if(Build.VERSION.SDK_INT>=29){
                ContentValues values=new ContentValues();values.put(MediaStore.MediaColumns.DISPLAY_NAME,"mobile-roundtrip.epub");values.put(MediaStore.MediaColumns.MIME_TYPE,"application/epub+zip");values.put(MediaStore.MediaColumns.RELATIVE_PATH,"Download/NorthDiaryQA");values.put(MediaStore.MediaColumns.IS_PENDING,1);
                Uri uri=getContext().getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,values);assertNotNull(uri);
                try(InputStream source=new FileInputStream(book);OutputStream out=getContext().getContentResolver().openOutputStream(uri)){assertNotNull(out);DiaryStore.copy(source,out,32*1024*1024);}
                values.clear();values.put(MediaStore.MediaColumns.IS_PENDING,0);getContext().getContentResolver().update(uri,values,null,null);
            }
        }finally{book.delete();}
    }
}
