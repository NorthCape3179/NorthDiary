package com.northcape.northdiary;

import android.content.*;
import android.security.keystore.*;
import android.util.Base64;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;
import java.security.KeyStore;
import java.nio.charset.StandardCharsets;
import java.io.IOException;

/** Credentials live outside diary archives, encrypted by an Android Keystore AES key. */
final class GitHubCredentialStore {
    private final SharedPreferences preferences;private final String alias;
    GitHubCredentialStore(Context c){this(c,"northdiary-github-account");}
    GitHubCredentialStore(Context c,String namespace){preferences=c.getSharedPreferences(namespace,0);alias=namespace+"-aes";}
    String login(){return preferences.getString("login","");}
    String authorization(){return preferences.getString("authorization","unknown");}
    String authorizationLabel(){
        switch(authorization()){
            case "oauth-repo":return "浏览器授权：已获得私有仓库权限（repo）";
            case "oauth-account":return "浏览器授权：仅账号权限，文集需重新授权";
            case "pat":return "专用令牌：仓库权限以连接结果为准";
            default:return "旧版登录：仓库权限尚未确认";
        }
    }
    private SecretKey key()throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);
        if(store.containsAlias(alias))return (SecretKey)store.getKey(alias,null);
        KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        generator.init(new KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
        return generator.generateKey();
    }
    void save(String token,String login)throws Exception {save(token,login,"unknown");}
    void save(String token,String login,String authorization)throws Exception {
        if(!java.util.Arrays.asList("unknown","oauth-repo","oauth-account","pat").contains(authorization))throw new IOException("授权类型无效");
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key());
        String encrypted=Base64.encodeToString(cipher.doFinal(token.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP),iv=Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP);
        if(!preferences.edit().putString("ciphertext",encrypted).putString("iv",iv).putString("login",login).putString("authorization",authorization).commit())throw new IOException("无法加密保存登录状态，请重试。");
    }
    String token()throws Exception {
        String encrypted=preferences.getString("ciphertext","");if(encrypted.isEmpty())return "";
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(preferences.getString("iv",""),Base64.NO_WRAP)));
        return new String(cipher.doFinal(Base64.decode(encrypted,Base64.NO_WRAP)),StandardCharsets.UTF_8);
    }
    void clear()throws Exception {
        if(!preferences.edit().clear().commit())throw new IOException("退出登录失败，请重试。");
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);if(store.containsAlias(alias))store.deleteEntry(alias);
    }
}
