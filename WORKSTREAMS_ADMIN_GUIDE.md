# Workstreams Admin Management Guide

## Overview
The admin dashboard provides full CRUD (Create, Read, Update, Delete) capabilities for all 4 workstreams:
- 🎙️ **Podcasts**
- 🎤 **Debators Circle** 
- 🎓 **Campus Edition**
- 🏘️ **UMV Mtaani**

---

## How to Access Workstreams

1. **Login as Admin** at `http://127.0.0.1:5000/auth/login`
2. **Navigate to Workstreams** - Click "Workstreams" in the left sidebar (grid icon)
3. **Dashboard View** - You'll see 4 cards, each showing:
   - Workstream name and description
   - Total item count
   - "View All" button to manage items
   - "Add New" button to create items

---

## 1️⃣ PODCASTS Management

### **View All Podcasts**
- **URL:** `/admin/podcasts`
- **Access:** Click "View All" on Podcasts card
- **Features:**
  - Filter by status (All, Published, Draft)
  - Filter by category
  - View counts: Total, Published, Draft
  - Each podcast shows: Title, Guest, Duration, Category, Status

### **Create New Podcast**
- **URL:** `/admin/podcasts/create`
- **Access:** Click "Add New" on Podcasts card OR "Create Podcast" button on podcasts list
- **Form Fields:**
  - Title* (required)
  - Description
  - Guest name
  - Audio URL
  - Thumbnail URL
  - Duration (minutes)
  - Category (Interview, Discussion, Story, Educational, etc.)
  - Published status (checkbox)
- **Submit:** Click "Create Podcast"
- **Result:** Redirects to `/admin/podcasts` with success message

### **Edit Podcast**
- **URL:** `/admin/podcasts/<podcast_id>/edit`
- **Access:** Click "Edit" button on any podcast in the list
- **Form Fields:** Same as Create (pre-filled with current values)
- **Submit:** Click "Update Podcast"
- **Result:** Redirects to `/admin/podcasts` with success message

### **Delete Podcast**
- **URL:** `/admin/podcasts/<podcast_id>/delete` (POST)
- **Access:** Click "Delete" button on any podcast
- **Confirmation:** Browser confirms deletion
- **Result:** Podcast permanently removed from database
- **Flash Message:** "Podcast deleted successfully"

---

## 2️⃣ DEBATORS CIRCLE Management

### **View All Debate Events**
- **URL:** `/admin/debates`
- **Access:** Click "View All" on Debators Circle card
- **Features:**
  - Filter by status (All, Upcoming, Ongoing, Completed, Cancelled)
  - Statistics: Total Debates, Upcoming, Completed
  - Each event shows: Title, Date, Status, Location, Organizer, Capacity
  - Color-coded status badges

### **Create New Debate Event**
- **URL:** `/admin/debates/create`
- **Access:** Click "Add New" on Debators Circle card OR "New Debate Event" button
- **Form Fields:**
  - Title* (required) - e.g., "Youth Mental Health Debate"
  - Description - What the debate will cover
  - Event Date & Time* (required) - Date/time picker
  - Registration Deadline - Optional cutoff date
  - Location - Venue or virtual link
  - Organizer - Host name or team
  - Max Participants - Optional capacity limit
  - Status - Upcoming (default), Ongoing, Completed, Cancelled
  - Cover Image URL - Optional hero image
- **Event Type:** Automatically set to `'debate'`
- **Submit:** Click "Create Event"
- **Result:** Redirects to `/admin/debates` with success message

### **Edit Debate Event**
- **URL:** `/admin/debates/<event_id>/edit`
- **Access:** Click "Edit" button on any debate event
- **Form Fields:** Same as Create (pre-filled)
- **Validation:** Only allows editing if `event_type` is 'debate' or 'Debaters Circle'
- **Submit:** Click "Update Event"
- **Result:** Updates event, redirects to `/admin/debates`

### **Delete Debate Event**
- **URL:** `/admin/debates/<event_id>/delete` (POST)
- **Access:** Click "Delete" button on any event
- **Validation:** Only allows deletion if event is Debaters Circle
- **Confirmation:** Browser confirms deletion
- **Result:** Event and all participations removed
- **Flash Message:** "Debaters Circle event deleted."

---

## 3️⃣ CAMPUS EDITION Management

### **View All Campus Events**
- **URL:** `/admin/campus-edition`
- **Access:** Click "View All" on Campus Edition card
- **Features:**
  - Filter by status (All, Upcoming, Ongoing, Completed, Cancelled)
  - Statistics: Total Events, Upcoming, Completed
  - Each event shows: Title, Date, Status, Location, Organizer
  - Same UI as Debate Events

### **Create New Campus Event**
- **URL:** `/admin/campus-edition/create`
- **Access:** Click "Add New" on Campus Edition card
- **Form Fields:** (Identical to Debate Events)
  - Title* (required)
  - Description
  - Event Date & Time* (required)
  - Registration Deadline
  - Location
  - Organizer
  - Max Participants
  - Status (Upcoming, Ongoing, Completed, Cancelled)
  - Cover Image URL
- **Event Type:** Automatically set to `'campus'`
- **Examples:** Campus workshops, student orientations, career fairs
- **Submit:** Click "Create Event"

### **Edit Campus Event**
- **URL:** `/admin/campus-edition/<event_id>/edit`
- **Access:** Click "Edit" on any campus event
- **Validation:** Only allows editing if `event_type` is 'campus'
- **Submit:** Click "Update Event"

### **Delete Campus Event**
- **URL:** `/admin/campus-edition/<event_id>/delete` (POST)
- **Access:** Click "Delete" button
- **Validation:** Only allows deletion if event is Campus Edition
- **Result:** Event permanently removed

---

## 4️⃣ UMV MTAANI Management

### **View All Mtaani Events**
- **URL:** `/admin/umv-mtaani`
- **Access:** Click "View All" on UMV Mtaani card
- **Features:**
  - Filter by status (All, Upcoming, Ongoing, Completed, Cancelled)
  - Statistics: Total Barazas, Upcoming, Completed
  - Community-focused event listings

### **Create New Mtaani Event**
- **URL:** `/admin/umv-mtaani/create`
- **Access:** Click "Add New" on UMV Mtaani card
- **Form Fields:** (Identical to other events)
  - Title* (required)
  - Description
  - Event Date & Time* (required)
  - Registration Deadline
  - Location - Community center or baraza venue
  - Organizer
  - Max Participants
  - Status
  - Cover Image URL
- **Event Type:** Automatically set to `'mtaani'`
- **Examples:** Community barazas, listening sessions, youth dialogues
- **Submit:** Click "Create Event"

### **Edit Mtaani Event**
- **URL:** `/admin/umv-mtaani/<event_id>/edit`
- **Access:** Click "Edit" on any mtaani event
- **Validation:** Only allows editing if `event_type` is 'mtaani'
- **Submit:** Click "Update Event"

### **Delete Mtaani Event**
- **URL:** `/admin/umv-mtaani/<event_id>/delete` (POST)
- **Access:** Click "Delete" button
- **Validation:** Only allows deletion if event is UMV Mtaani
- **Result:** Event permanently removed

---

## Complete URL Reference

### Podcasts
```
List:   GET  /admin/podcasts
Create: GET  /admin/podcasts/create
        POST /admin/podcasts/create
Edit:   GET  /admin/podcasts/<id>/edit
        POST /admin/podcasts/<id>/edit
Delete: POST /admin/podcasts/<id>/delete
```

### Debators Circle
```
List:   GET  /admin/debates
Create: GET  /admin/debates/create
        POST /admin/debates/create
Edit:   GET  /admin/debates/<id>/edit
        POST /admin/debates/<id>/edit
Delete: POST /admin/debates/<id>/delete
```

### Campus Edition
```
List:   GET  /admin/campus-edition
Create: GET  /admin/campus-edition/create
        POST /admin/campus-edition/create
Edit:   GET  /admin/campus-edition/<id>/edit
        POST /admin/campus-edition/<id>/edit
Delete: POST /admin/campus-edition/<id>/delete
```

### UMV Mtaani
```
List:   GET  /admin/umv-mtaani
Create: GET  /admin/umv-mtaani/create
        POST /admin/umv-mtaani/create
Edit:   GET  /admin/umv-mtaani/<id>/edit
        POST /admin/umv-mtaani/<id>/edit
Delete: POST /admin/umv-mtaani/<id>/delete
```

---

## Access Control

✅ **All routes protected with:**
- `@login_required` - Must be logged in
- `@admin_required` - Must have Admin role

❌ **Supervisors and Champions cannot:**
- Access workstreams dashboard
- Create, edit, or delete any workstream content
- View admin-specific routes

---

## Database Structure

### Events Table
All 3 event workstreams (Debators Circle, Campus Edition, UMV Mtaani) use the same `events` table:

```python
Event:
  - event_id (PK)
  - title
  - description
  - event_date
  - location
  - event_type ('debate', 'campus', 'mtaani')  ← Distinguishes workstreams
  - organizer
  - max_participants
  - registration_deadline
  - status (Upcoming, Ongoing, Completed, Cancelled)
  - image_url
  - created_at
  - updated_at
  - created_by (FK to users)
```

### Podcasts Table
```python
Podcast:
  - podcast_id (PK)
  - title
  - description
  - guest
  - audio_url
  - thumbnail_url
  - duration
  - category
  - published (boolean)
  - created_at
  - updated_at
```

---

## Step-by-Step Example: Creating a Debate Event

1. **Navigate:** Login → Workstreams → Debators Circle → "Add New"
2. **Fill Form:**
   - Title: "Mental Health Stigma Debate"
   - Description: "Discussing strategies to reduce mental health stigma in youth"
   - Event Date: 2026-02-15 14:00
   - Location: "Nairobi Community Hall"
   - Organizer: "UNDA Program Team"
   - Max Participants: 50
   - Status: Upcoming
3. **Submit:** Click "Create Event"
4. **Result:** Event appears in `/admin/debates` list
5. **Edit:** Click "Edit" → Change title → "Update Event"
6. **Delete:** Click "Delete" → Confirm → Event removed

---

## Navigation Flow

```
Admin Dashboard
    ↓
Workstreams (Sidebar)
    ↓
[4 Workstream Cards]
    ↓
┌─────────────┬──────────────┬───────────────┬────────────┐
│  Podcasts   │ Debators     │ Campus        │ UMV Mtaani │
│  View All → │ Circle       │ Edition       │ View All → │
│  Add New →  │ View All →   │ View All →    │ Add New →  │
└─────────────┴──────────────┴───────────────┴────────────┘
         ↓             ↓             ↓             ↓
    [List View]  [List View]  [List View]  [List View]
         ↓             ↓             ↓             ↓
    Create/Edit/Delete for each workstream
```

---

## Summary

✅ **Yes, admins can fully manage all 4 workstreams:**
- ✅ **Create** new items with comprehensive forms
- ✅ **Read/View** all items with filtering and statistics
- ✅ **Update** existing items with edit forms
- ✅ **Delete** items with confirmation

All operations are accessible through the unified Workstreams dashboard with consistent UI patterns across all workstreams.
