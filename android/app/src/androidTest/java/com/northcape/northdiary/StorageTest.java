package com.northcape.northdiary;

import android.test.AndroidTestCase;
import java.io.*;
import java.util.*;
import java.util.zip.*;
import static com.northcape.northdiary.Models.*;

public class StorageTest extends AndroidTestCase {
    private File root;
    private DiaryStore store;
    @Override protected void setUp()throws Exception {super.setUp();root=new File(getContext().getCacheDir(),"test-"+UUID.randomUUID());store=new DiaryStore(getContext(),root);}
    @Override protected void tearDown()throws Exception {store.close();ArchiveService.remove(root);super.tearDown();}
    private Article article(){Article a=new Article();a.id=UUID.randomUUID().toString();a.title="回忆";a.date="2026";a.html="<p>中文正文</p>";a.text="中文正文";return a;}
    public void testAtomicSaveAndRetry(){
        Article a=article();a.people.add(UUID.randomUUID().toString());
        try{store.save(a);fail("missing person must roll back");}catch(RuntimeException expected){}
        assertEquals("",a.created);assertEquals(0,store.list("","",0,false,null).size());
        a.people.clear();store.save(a);assertEquals("2026-未知-未知",store.get(a.id).date);
    }
    public void testRelationshipsOutsideSearchAndTrash(){
        Person p=new Person();p.id=UUID.randomUUID().toString();p.name="同学";p.code="A";store.savePerson(p);
        Article a=article();a.outside=true;a.people.add(p.id);a.tags.add("校园");store.save(a);
        assertEquals(0,store.list("","",0,true,null).size());assertEquals(1,store.list("中文","校园",1,false,p.id).size());
        p.name="朋友";store.savePerson(p);assertEquals(p.id,store.get(a.id).people.get(0));
        store.deletePerson(p.id);assertTrue(store.get(a.id).people.isEmpty());
        store.deleted(a.id,true);assertEquals(0,store.list("","",1,false,null).size());assertEquals(1,store.list("","",3,false,null).size());
        store.deleted(a.id,false);assertEquals(1,store.list("","",1,false,null).size());
    }
    public void testDraftSurvivesInvalidDate()throws Exception {
        Article a=article();a.date="正在输入";DraftStore drafts=new DraftStore(root);drafts.write(a);
        try{store.save(a);fail();}catch(IllegalArgumentException expected){}
        assertEquals("正在输入",drafts.read().date);assertEquals("中文正文",drafts.read().text);
    }
    public void testBackupRoundTripWithImageAndPeople()throws Exception {
        Article a=article();store.save(a);Attachment image=new Attachment();image.id=UUID.randomUUID().toString();image.name="图片.png";
        image.path="attachments/"+image.id+".png";image.mime="image/png";
        try(OutputStream out=new FileOutputStream(new File(root,image.path))){out.write(new byte[]{1,2,3});}
        store.addAttachment(a.id,image);File zip=ArchiveService.export(getContext(),store);File staged=null;
        try {
            staged=ArchiveService.stage(getContext(),new FileInputStream(zip));
            try(DiaryStore restored=new DiaryStore(getContext(),staged)) {
                assertEquals(a.html,restored.get(a.id).html);assertEquals(image.name,restored.attachments(a.id).get(0).name);
                assertEquals(3,new File(staged,image.path).length());
            }
        }finally{zip.delete();if(staged!=null)ArchiveService.remove(staged);}
    }
    public void testTraversalAndMissingAttachmentsRejected()throws Exception {
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        try(ZipOutputStream z=new ZipOutputStream(bytes)){z.putNextEntry(new ZipEntry("../escape"));z.write(1);z.closeEntry();}
        try{ArchiveService.stage(getContext(),new ByteArrayInputStream(bytes.toByteArray()));fail();}catch(IOException expected){}
        Article a=article();store.save(a);Attachment image=new Attachment();image.id=UUID.randomUUID().toString();image.name="missing";image.path="attachments/missing.png";image.mime="image/png";store.addAttachment(a.id,image);
        try{ArchiveService.validate(root);fail();}catch(IOException expected){}
        assertEquals(a.title,store.get(a.id).title);
    }
}
