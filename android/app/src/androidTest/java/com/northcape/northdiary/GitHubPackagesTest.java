package com.northcape.northdiary;

import android.content.Context;
import android.test.AndroidTestCase;
import android.util.Base64;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class GitHubPackagesTest extends AndroidTestCase {
    private static final String REPO="qa/NorthDiary-Data",TOKEN="dummy-test-private-token",HEAD=String.join("",Collections.nCopies(40,"a"));
    private File root,book;private byte[] data;
    @Override protected void setUp()throws Exception{
        super.setUp();root=new File(getContext().getCacheDir(),"github-packs-"+UUID.randomUUID());assertTrue(root.mkdirs());book=new File(root,"test.epub");Context tests=getContext().createPackageContext("com.northcape.northdiary.test",0);
        try(InputStream in=tests.getAssets().open("desktop-v4.epub.base64")){data=Base64.decode(DiaryStore.readBytes(in,128*1024),Base64.DEFAULT);}try(OutputStream out=new FileOutputStream(book)){out.write(data);}
    }
    @Override protected void tearDown()throws Exception{ArchiveService.remove(root);super.tearDown();}
    private final class Fake implements GitHubPackagesApi.Transport {
        boolean privateRepo=true,writable=true,initialized=true,nonempty=false,corrupt=false,badAck=false;int forced=0,puts=0,calls=0;
        final Map<String,byte[]> packs=new LinkedHashMap<>();final List<String> paths=new ArrayList<>();
        public GitHubPackagesApi.Response request(String method,String path,String token,JSONObject body,File upload,boolean raw,File destination,long limit)throws Exception{
            assertEquals(TOKEN,token);calls++;paths.add(path);if(forced!=0)return new GitHubPackagesApi.Response(forced,"");String base="/repos/"+REPO;
            if(path.equals(base))return new GitHubPackagesApi.Response(200,new JSONObject().put("private",privateRepo).put("full_name",REPO).put("default_branch","notes/main").put("permissions",new JSONObject().put("push",writable)).toString());
            if(path.startsWith(base+"/contents/"+GitHubPackagesApi.MARKER)){
                if(method.equals("PUT")){assertFalse(nonempty);assertFalse(initialized);assertNull(upload);JSONObject marker=new JSONObject(new String(Base64.decode(body.getString("content"),Base64.DEFAULT),StandardCharsets.UTF_8));assertEquals("NorthDiaryData",marker.getString("format"));initialized=true;puts++;return new GitHubPackagesApi.Response(201,"{}");}
                assertTrue(raw);return new GitHubPackagesApi.Response(initialized?200:404,initialized?"{\"format\":\"NorthDiaryData\",\"version\":1}":"");
            }
            if(path.equals(base+"/contents/"))return new GitHubPackagesApi.Response(200,nonempty?"[{\"name\":\"main.py\"}]":"[]");
            if(path.equals(base+"/branches/notes%2Fmain"))return new GitHubPackagesApi.Response(200,"{\"commit\":{\"sha\":\""+HEAD+"\"}}");
            if(path.equals(base+"/contents/packs?ref="+HEAD)){
                JSONArray list=new JSONArray();for(Map.Entry<String,byte[]> entry:packs.entrySet()){File file=new File(root,"digest");try(OutputStream out=new FileOutputStream(file)){out.write(entry.getValue());}list.put(new JSONObject().put("name",entry.getKey()).put("type","file").put("path","packs/"+entry.getKey()).put("size",entry.getValue().length).put("sha",GitHubPackagesApi.blobSha(file)));file.delete();}return new GitHubPackagesApi.Response(200,list.toString());
            }
            if(path.startsWith(base+"/contents/packs/")){
                String name=path.substring((base+"/contents/packs/").length()).split("\\?")[0];assertTrue(name.matches(GitHubPackagesApi.NAME));
                if(method.equals("PUT")){assertEquals("notes/main",body.getString("branch"));assertFalse(body.has("sha"));assertNotNull(upload);assertFalse(packs.containsKey(name));byte[] bytes;try(InputStream in=new FileInputStream(upload)){bytes=DiaryStore.readBytes(in,GitHubPackagesApi.MAX_PACKAGE);}packs.put(name,bytes);puts++;String sha=badAck?String.join("",Collections.nCopies(40,"0")):GitHubPackagesApi.blobSha(upload);return new GitHubPackagesApi.Response(201,"{\"content\":{\"sha\":\""+sha+"\"}}");}
                assertTrue(path.endsWith("?ref="+HEAD));assertTrue(raw);assertNotNull(destination);byte[] bytes=packs.get(name).clone();if(corrupt)bytes[0]^=1;try(OutputStream out=new FileOutputStream(destination)){out.write(bytes);}return new GitHubPackagesApi.Response(200,"");
            }
            throw new AssertionError("Unexpected API route: "+method+" "+path);
        }
    }
    public void testPrivateRepositoryUploadPinnedDownloadAndPreviewMerge()throws Exception{
        Fake remote=new Fake();GitHubPackagesApi api=new GitHubPackagesApi(root,TOKEN,remote);String name=api.upload(REPO,book);assertTrue(name.matches(GitHubPackagesApi.NAME));assertEquals(1,remote.puts);assertTrue(Arrays.equals(data,remote.packs.get(name)));
        List<GitHubPackagesApi.Package> list=api.list(REPO);assertEquals(1,list.size());assertEquals(HEAD,list.get(0).commit);File downloaded=api.download(REPO,list.get(0));
        try(DiaryStore store=new DiaryStore(getContext(),new File(root,"store"));InputStream in=new FileInputStream(downloaded)){
            EpubImportService.Preview preview=EpubImportService.prepare(getContext(),store,in);try{assertEquals(2,preview.fresh);assertEquals(0,store.exportable().size());assertEquals(2,EpubImportService.apply(store,preview).imported);}finally{preview.close(false);}
        }finally{downloaded.delete();}
    }
    public void testPublicAndSourceRepositoriesBlockedAndEmptyInitializationExplicit()throws Exception{
        Fake remote=new Fake();remote.privateRepo=false;GitHubPackagesApi api=new GitHubPackagesApi(root,TOKEN,remote);try{api.upload(REPO,book);fail();}catch(IOException expected){}assertEquals(0,remote.puts);assertEquals(1,remote.calls);
        remote=new Fake();api=new GitHubPackagesApi(root,TOKEN,remote);try{api.checkRepository("qa/NorthDiary");fail();}catch(IOException expected){}assertEquals(0,remote.calls);
        remote=new Fake();remote.initialized=false;remote.nonempty=true;api=new GitHubPackagesApi(root,TOKEN,remote);try{api.initializeRepository(REPO);fail();}catch(IOException expected){}assertEquals(0,remote.puts);
        remote.nonempty=false;api.initializeRepository(REPO);assertEquals(1,remote.puts);assertTrue(remote.initialized);api.initializeRepository(REPO);assertEquals(1,remote.puts);
    }
    public void testReadOnlyBadAcknowledgementAndCorruptedDownloadRejected()throws Exception{
        Fake remote=new Fake();remote.writable=false;GitHubPackagesApi api=new GitHubPackagesApi(root,TOKEN,remote);try{api.upload(REPO,book);fail();}catch(IOException expected){}assertEquals(0,remote.puts);
        remote.writable=true;remote.badAck=true;try{api.upload(REPO,book);fail();}catch(IOException expected){assertTrue(expected.getMessage().contains("刷新"));}assertEquals(1,remote.puts);
        GitHubPackagesApi.Package pack=api.list(REPO).get(0);remote.corrupt=true;int before=Objects.requireNonNull(root.list()).length;try{api.download(REPO,pack);fail();}catch(IOException expected){}assertEquals(before,Objects.requireNonNull(root.list()).length);
        for(int code:new int[]{401,403,404,409,422,429}){remote.forced=code;try{api.checkRepository(REPO);fail();}catch(GitHubPackagesApi.Failure expected){assertEquals(code,expected.status);assertFalse(expected.getMessage().contains(TOKEN));}}
    }
    public void testStreamingBodyAndPackageSizeGuard()throws Exception{
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();GitHubPackagesApi.writeUploadBody(bytes,new JSONObject().put("message","测试上传").put("branch","notes/main"),book);JSONObject json=new JSONObject(bytes.toString("UTF-8"));assertEquals("notes/main",json.getString("branch"));assertTrue(Arrays.equals(data,Base64.decode(json.getString("content"),Base64.DEFAULT)));
        File big=new File(root,"large.epub");try(RandomAccessFile file=new RandomAccessFile(big,"rw")){file.setLength(GitHubPackagesApi.MAX_PACKAGE+1);}Fake remote=new Fake();try{new GitHubPackagesApi(root,TOKEN,remote).upload(REPO,big);fail();}catch(IOException expected){}assertEquals(0,remote.calls);
    }
}
