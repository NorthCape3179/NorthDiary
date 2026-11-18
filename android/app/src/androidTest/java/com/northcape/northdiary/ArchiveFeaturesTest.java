package com.northcape.northdiary;

import android.graphics.Bitmap;
import android.test.AndroidTestCase;
import org.w3c.dom.Document;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
import static com.northcape.northdiary.Models.*;

public class ArchiveFeaturesTest extends AndroidTestCase {
    private File root;private DiaryStore store;
    @Override protected void setUp()throws Exception{super.setUp();root=new File(getContext().getCacheDir(),"feature-"+UUID.randomUUID());store=new DiaryStore(getContext(),root);}
    @Override protected void tearDown()throws Exception{store.close();ArchiveService.remove(root);super.tearDown();}
    private Article article(String title,boolean outside){Article a=new Article();a.id=UUID.randomUUID().toString();a.title=title;a.date="2026";a.outside=outside;a.html="<p>正文</p>";a.text="正文";a.categories=new ArrayList<>(Arrays.asList("校园","往事"));a.tags.add("回忆");store.save(a);return a;}
    public void testCategoriesFilterDraftRecoveryAndRollback()throws Exception{
        Article a=article("一篇",false);Article b=article("另一篇",false);b.categories=Collections.singletonList("旅行");store.save(b);
        assertEquals(a.id,store.list("","回忆","校园",0,true,null).get(0).id);
        Article edit=store.get(a.id);edit.categories=Collections.singletonList("新分类");DraftStore draft=new DraftStore(root);draft.write(edit);assertEquals(edit.categories,draft.read().categories);
        edit.people.add("missing-person");try{store.save(edit);fail();}catch(RuntimeException expected){}
        assertTrue(store.get(a.id).categories.contains("校园"));edit.people.clear();store.save(edit);assertEquals(Collections.singletonList("新分类"),store.get(a.id).categories);
        // Legacy journals have no category property and must not erase existing relationships.
        edit.categories=null;draft.write(edit);Article legacy=draft.read();assertNull(legacy.categories);store.save(legacy);assertEquals(Collections.singletonList("新分类"),store.get(a.id).categories);
    }
    private String read(ZipFile zip,String path)throws Exception{try(InputStream in=zip.getInputStream(zip.getEntry(path))){return new String(DiaryStore.readBytes(in,16*1024*1024),StandardCharsets.UTF_8);}}
    private Document xml(String text)throws Exception{DocumentBuilderFactory factory=DocumentBuilderFactory.newInstance();factory.setNamespaceAware(true);return factory.newDocumentBuilder().parse(new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));}
    public void testEpubOrderXmlLinksImagesAndSourcePreserved()throws Exception{
        Article dated=article("有日期 < & 中文",false),outside=article("无日期的回忆",true);
        Attachment image=new Attachment();image.id=UUID.randomUUID().toString();image.name="照片 < & >.png";image.mime="image/png";image.path="attachments/"+image.id+".png";
        Bitmap bitmap=Bitmap.createBitmap(2,2,Bitmap.Config.ARGB_8888);try(OutputStream out=new FileOutputStream(new File(root,image.path))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}bitmap.recycle();store.addAttachment(dated.id,image);
        dated.html="<!--northdiary-paragraphs-v1--><p style=\"text-align:center\"><b>中文加粗</b> &amp; <i>斜体</i></p><p style=\"text-indent:2em\"><a href=\"ndiary-image:"+image.id+"\">照片</a></p><p><a href=\"https://example.com/?a=1&amp;b=2\">网址</a></p>";store.save(dated);
        String original=store.get(dated.id).html,updated=store.get(dated.id).updated;
        File file=EpubService.export(getContext(),store,Arrays.asList(outside.id,dated.id),"文集 & <测试>","作者");
        try(ZipFile zip=new ZipFile(file)){
            ZipEntry first=zip.entries().nextElement();assertEquals("mimetype",first.getName());assertEquals(ZipEntry.STORED,first.getMethod());assertEquals("application/epub+zip",read(zip,"mimetype"));
            xml(read(zip,"META-INF/container.xml"));xml(read(zip,"EPUB/content.opf"));xml(read(zip,"EPUB/nav.xhtml"));
            String one=read(zip,"EPUB/text/chapter-1.xhtml"),two=read(zip,"EPUB/text/chapter-2.xhtml");xml(one);xml(two);
            assertTrue(one.contains(outside.title));assertFalse(one.contains("class=\"date\""));assertTrue(two.contains("class=\"date\""));
            assertTrue(two.contains("<strong>中文加粗</strong>"));assertTrue(two.contains("text-align:center"));assertTrue(two.contains("text-indent:2em"));assertTrue(two.contains("<em>斜体</em>"));
            assertFalse(two.contains("ndiary-image:"));assertFalse(two.contains("<img"));assertTrue(two.contains("../images/image-1.png"));assertTrue(two.contains("照片 &lt; &amp; &gt;.png"));assertNotNull(zip.getEntry("EPUB/images/image-1.png"));
        }finally{file.delete();}
        assertEquals(original,store.get(dated.id).html);assertEquals(updated,store.get(dated.id).updated);
    }
    public void testExportRejectsDraftTrashDuplicateAndMissingOrUnsafeAttachment()throws Exception{
        Article a=article("正常",false);Article draft=article("待写",false);draft.draft=true;store.save(draft);Article trash=article("回收站",false);store.deleted(trash.id,true);
        assertEquals(1,store.exportable().size());
        for(List<String> ids:Arrays.asList(Arrays.asList(a.id,a.id),Collections.singletonList(draft.id),Collections.singletonList(trash.id),Collections.<String>emptyList())){
            try{EpubService.export(getContext(),store,ids,"文集","");fail();}catch(IOException expected){}
        }
        Attachment image=new Attachment();image.id=UUID.randomUUID().toString();image.name="缺失.png";image.path="attachments/missing.png";image.mime="image/png";store.addAttachment(a.id,image);
        try{EpubService.export(getContext(),store,Collections.singletonList(a.id),"文集","");fail();}catch(IOException expected){}
        store.getWritableDatabase().execSQL("UPDATE attachments SET relative_path='../outside.png' WHERE id=?",new Object[]{image.id});
        try{EpubService.export(getContext(),store,Collections.singletonList(a.id),"文集","");fail();}catch(IOException expected){}
        assertEquals(a.title,store.get(a.id).title);
    }
    public void testRandomCandidatesNoRepeatAndNoWrites(){
        Article a=article("第一篇",false),b=article("第二篇",true),draft=article("待写",false);draft.draft=true;store.save(draft);Article trash=article("已删除",false);store.deleted(trash.id,true);
        List<Article> candidates=store.exportable();assertEquals(2,candidates.size());String before=store.get(a.id).updated;
        assertEquals(b.id,RandomMemoryDialog.pick(candidates,a.id,new Random(1)).id);assertEquals(a.id,RandomMemoryDialog.pick(candidates,b.id,new Random(1)).id);
        assertEquals(a.id,RandomMemoryDialog.pick(Collections.singletonList(store.get(a.id)),a.id,new Random(1)).id);assertNull(RandomMemoryDialog.pick(Collections.emptyList(),"",new Random(1)));
        assertEquals(before,store.get(a.id).updated);
    }
}
