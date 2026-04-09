# Cloudinary Integration Guide

This application now supports Cloudinary as a cloud storage provider for media files. This guide explains how to set up and use Cloudinary.

## What Changed

The application now supports three storage backends in this priority order:

1. **Cloudinary** (if `CLOUDINARY_CLOUD_NAME` is set) - RECOMMENDED for production
2. **AWS S3** (if `AWS_S3_BUCKET` is set)
3. **Local Filesystem** (default fallback)

## Benefits of Using Cloudinary

- ✅ **No persistency concerns** - Files persist across server restarts
- ✅ **Built-in image transformations** - Automatic thumbnail generation, resizing, format conversion
- ✅ **CDN delivery** - Fast global distribution
- ✅ **Easy management** - Dashboard to view and manage all files
- ✅ **Security** - Signed URLs, access control
- ✅ **Cost-effective** - Free tier available for testing
- ✅ **Video support** - Streaming videos with transformations
- ✅ **Analytics** - Usage tracking and insights

## Setup Instructions

### 1. Create a Cloudinary Account

1. Go to https://cloudinary.com/users/register
2. Sign up for a free account
3. Verify your email
4. Go to your [Dashboard](https://cloudinary.com/console/c/)

### 2. Get Your Credentials

From the Cloudinary Dashboard:

- **Cloud Name**: Visible at the top (e.g., `djkahfker`)
- **API Key**: Under "Settings" > "Access Credentials"
- **API Secret**: Under "Settings" > "Access Credentials" (keep this secret!)

### 3. Set Environment Variables

Add these to your `.env` file or deployment platform environment variables:

```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

For **Render**, **Heroku**, or other platforms:
- Add these as environment variables in your deployment settings
- Restart the application after adding

### 4. Deploy and Test

1. Commit changes:
   ```bash
   git add .
   git commit -m "Enable Cloudinary cloud storage integration"
   git push
   ```

2. Files uploaded to media galleries will now be stored on Cloudinary
3. Check the Cloudinary Dashboard to verify files are being uploaded

## How It Works

### Uploading Files

When you upload files through the admin interface:

1. File is validated (extension, size)
2. Sent to Cloudinary API
3. Stored with a public folder structure (e.g., `media_galleries/20260408...jpg`)
4. Cloudinary returns a permanent URL (e.g., `https://res.cloudinary.com/...`)
5. URL is stored in the database
6. Database record points to Cloudinary URL, not local filesystem

### Serving Files

When clients request media:

1. Database returns the Cloudinary URL
2. App redirects to the permanent Cloudinary CDN URL
3. Client downloads from Cloudinary's global CDN

### Deleting Files

When you delete a gallery:

1. App deletes database record
2. App calls Cloudinary API to delete files
3. Cloudinary removes files from storage

## Migration from Local Storage

### Option 1: Start Fresh (Recommended)
- Simply enable Cloudinary with environment variables
- New uploads go to Cloudinary
- Old local files remain on local filesystem (won't be served if you disable local storage)

### Option 2: Migrate Existing Files
A migration script can be created to upload existing local files to Cloudinary:

```bash
# To be created on-demand
python scripts/migrate_to_cloudinary.py
```

This would:
1. Find all media files in `instance/uploads/`
2. Upload each to Cloudinary
3. Update database records with Cloudinary URLs
4. Optionally delete local files

## Configuration Options

### Priority Switching

To change which storage backend is used, set environment variables:

```bash
# Enable Cloudinary (highest priority)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Cloudinary will be used if set; otherwise falls back to S3 or local storage
```

To use S3 instead of Cloudinary:
```bash
# Unset Cloudinary variables, then set S3
AWS_S3_BUCKET=your_bucket
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Advanced Cloudinary Settings

The integration uses sensible defaults. For advanced configuration, edit `app.py`:

```python
# Examples for future customization:
# - Custom folder structure
# - Custom naming patterns
# - Upload presets
# - Transformation defaults
```

## Troubleshooting

### "Cloudinary initialization failed"
- Check that all three environment variables are set correctly
- Verify API Key and Secret are correct (not swapped)
- Check network connectivity to cloudinary.com

### "File upload failed"
- Check file size (max 10MB by default)
- Verify file type is allowed
- Check Cloudinary dashboard for upload limit exceeded (free tier limit)
- Check API credentials haven't been revoked

### Files not appearing in Cloudinary Dashboard
- Check that `CLOUDINARY_CLOUD_NAME` is correct
- Verify the application is actually using Cloudinary (check logs)
- Check firewall/proxy isn't blocking Cloudinary API calls

### Reverting to Local Storage
Simply remove all Cloudinary environment variables and restart the app. It will fall back to local filesystem.

## Cost Considerations

**Cloudinary Free Tier:**
- 25 GB monthly uploads
- 25 GB stored files
- 1 GB monthly transformations
- Duration limit: 25 hours of video

For most small/medium applications, this is sufficient. Enterprise plans available for higher volumes.

## Security Best Practices

1. **Rotate API Secret regularly** if exposed
2. **Never commit credentials** to version control
3. **Use environment variables** for all sensitive data
4. **Consider API access restrictions** in Cloudinary settings
5. **Enable upload authentication** in production
6. **Use secure URLs** (https) always

## API Reference

### Configuration (in app.py)
```python
app.config['USE_CLOUDINARY']           # Boolean: True if enabled
app.config['CLOUDINARY_CLOUD_NAME']    # Your cloud name
app.config['CLOUDINARY_API_KEY']       # Your API key
app.config['CLOUDINARY_API_SECRET']    # Your API secret
```

### File Storage (services/file_utils.py)
- `save_file(fileobj, subdir)` - Automatically uploads to Cloudinary if enabled
- `generate_thumbnail(url, size)` - Uses Cloudinary transformations for images

### Utilities (services/cloudinary_utils.py)
- `delete_cloudinary_file(url)` - Delete a single file
- `delete_media_files(media_items)` - Delete multiple files
- Supports mixed Cloudinary/S3/local files

## Next Steps

1. ✅ Set up Cloudinary account
2. ✅ Add environment variables
3. ✅ Deploy changes
4. ✅ Test file upload in admin interface
5. ✅ Verify files appear in Cloudinary Dashboard
6. ✅ Check CDN URLs work in frontend
7. 📋 Monitor storage usage
8. 📋 Adjust upload folder structure if needed

## Support

For issues:
1. Check Cloudinary Dashboard > Logs
2. Enable debug logging in Flask
3. Test API credentials with curl: `curl -u {api_key}:{api_secret} https://api.cloudinary.com/v1_1/{cloud_name}/resources/image`
4. Review this guide for common issues

## References

- [Cloudinary Documentation](https://cloudinary.com/documentation)
- [Cloudinary Python SDK](https://cloudinary.com/documentation/python_integration)
- [Upload API Reference](https://cloudinary.com/documentation/upload_api)
