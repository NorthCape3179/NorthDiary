package com.northcape.northdiary;

import android.content.*;
import android.database.*;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.*;
import static com.northcape.northdiary.Models.*;

/** Grants a viewer read access to one managed attachment, never to a directory. */
public final class AttachmentProvider extends ContentProvider {
    @Override public boolean onCreate() { return true; }
    private Attachment find(Uri uri) throws FileNotFoundException {
        String id=uri.getLastPathSegment();
        if(uri.getPathSegments().size()!=1||id==null||!id.matches("[A-Za-z0-9-]+")) throw new FileNotFoundException();
        try(DiaryStore store=new DiaryStore(getContext(),DiaryStore.activeRoot(getContext()));
            Cursor c=store.getReadableDatabase().rawQuery("SELECT id,name,relative_path,mime_type FROM attachments WHERE id=?",new String[]{id})) {
            if(!c.moveToFirst())throw new FileNotFoundException();
            Attachment a=new Attachment(); a.id=c.getString(0); a.name=c.getString(1); a.path=c.getString(2); a.mime=c.getString(3); return a;
        }
    }
    @Override public ParcelFileDescriptor openFile(Uri uri,String mode) throws FileNotFoundException {
        if(!"r".equals(mode))throw new FileNotFoundException("只读附件");
        try { return ParcelFileDescriptor.open(ArchiveService.attachmentFile(DiaryStore.activeRoot(getContext()),find(uri).path),ParcelFileDescriptor.MODE_READ_ONLY); }
        catch(IOException e) { throw new FileNotFoundException(e.getMessage()); }
    }
    @Override public String getType(Uri uri) { try {return find(uri).mime;}catch(FileNotFoundException e){return "application/octet-stream";} }
    @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String sort) {
        try {
            Attachment a=find(uri); String[] columns=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;
            MatrixCursor result=new MatrixCursor(columns); Object[] row=new Object[columns.length];
            for(int i=0;i<columns.length;i++) {
                if(columns[i].equals(OpenableColumns.DISPLAY_NAME))row[i]=a.name;
                else if(columns[i].equals(OpenableColumns.SIZE))row[i]=ArchiveService.attachmentFile(DiaryStore.activeRoot(getContext()),a.path).length();
            } result.addRow(row); return result;
        }catch(IOException e){return null;}
    }
    @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
    @Override public int update(Uri uri,ContentValues values,String s,String[] args){throw new UnsupportedOperationException();}
    @Override public int delete(Uri uri,String s,String[] args){throw new UnsupportedOperationException();}
}
