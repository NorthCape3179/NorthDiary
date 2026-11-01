package com.northcape.northdiary;

import android.test.AndroidTestCase;
import org.json.JSONObject;
import java.io.IOException;
import java.util.UUID;

public class GitHubAuthTest extends AndroidTestCase {
    public void testDeviceFlowPendingSlowDownSuccessAndAccountValidation()throws Exception {
        int[] calls={0};GitHubAuthApi api=new GitHubAuthApi((url,token,form)->{
            if(url.equals(GitHubAuthApi.DEVICE)){assertEquals("read:user",form.get("scope"));assertEquals("",token);return new JSONObject("{\"verification_uri\":\"https://github.com/login/device\",\"user_code\":\"ABCD-EFGH\",\"device_code\":\"test-device\",\"interval\":5,\"expires_in\":900}");}
            if(url.equals(GitHubAuthApi.USER)){assertEquals("unit-test-access-token",token);return new JSONObject("{\"login\":\"test-account\",\"id\":123}");}
            assertEquals("urn:ietf:params:oauth:grant-type:device_code",form.get("grant_type"));assertEquals("",token);
            int n=calls[0]++;return new JSONObject(n==0?"{\"error\":\"authorization_pending\"}":n==1?"{\"error\":\"slow_down\"}":"{\"access_token\":\"unit-test-access-token\",\"token_type\":\"bearer\"}");
        });
        GitHubAuthApi.Challenge challenge=api.start("test-client");assertEquals("authorization_pending",api.poll("test-client",challenge).state);assertEquals("slow_down",api.poll("test-client",challenge).state);
        assertEquals("test-account",api.user(api.poll("test-client",challenge).token));
    }
    public void testUntrustedVerificationUrlAndDeniedAuthorizationAreRejected()throws Exception {
        GitHubAuthApi bad=new GitHubAuthApi((u,t,f)->new JSONObject("{\"verification_uri\":\"https://example.invalid/login\"}"));
        try{bad.start("test-client");fail();}catch(IOException expected){}
        GitHubAuthApi denied=new GitHubAuthApi((u,t,f)->new JSONObject("{\"error\":\"access_denied\"}"));
        try{denied.poll("test-client",new GitHubAuthApi.Challenge("ABCD","device",5,900));fail();}catch(IOException expected){}
        try{denied.user("unsafe\r\nheader");fail();}catch(IOException expected){}
    }
    public void testCredentialEncryptionAndForgetAreIndependentOfDiaryBackup()throws Exception {
        String namespace="github-test-"+UUID.randomUUID(),secret="dummy-test-credential-never-used-on-network";GitHubCredentialStore vault=new GitHubCredentialStore(getContext(),namespace);
        try{vault.save(secret,"test-account");assertEquals(secret,vault.token());assertEquals("test-account",vault.login());assertFalse(getContext().getSharedPreferences(namespace,0).getAll().toString().contains(secret));vault.clear();assertEquals("",vault.token());}
        finally{vault.clear();}
    }
}
