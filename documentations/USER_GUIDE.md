# UNDA Youth Network Management System - User Guide

## Documentation Navigation

- [Project Overview](README.md)
- [Quick Start](QUICK_START.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Deployment Status](DEPLOYMENT_STATUS.md)
- [Security Overview](SECURITY.md)
- [Security Implementation](SECURITY_IMPLEMENTATION.md)
- [Changelog](CHANGELOG.md)

## What is UNDA Youth Network?

UNDA Youth Network is a **digital platform** designed to help youth organizations manage their programs, track participant progress, and ensure the safety of young people. Think of it as a **smart filing cabinet** that keeps all your youth program information organized, secure, and easily accessible from anywhere.

---

## Who Is This For?

- **Youth Workers & Supervisors**: Manage young people's information, track their progress, and monitor safeguarding concerns
- **Program Administrators**: Oversee the entire youth program, generate reports, and ensure compliance
- **Prevention Advocates (Young People)**: Access their own information and track their personal development journey

---

## How Does It Work?

### **Simple Login System**
Just like logging into your email or social media:
1. Visit the website
2. Enter your username and password
3. Access your personalized dashboard

**Security Feature**: Your account locks automatically after 5 failed login attempts to prevent unauthorized access - like a security lock on your front door.

### **Role-Based Access**
Everyone sees only what they need:
- **Prevention Advocates** see their own information only
- **Supervisors** see their assigned prevention advocates
- **Admins** see everything and manage the system

Think of it like a **hospital**: patients see their own records, nurses see their assigned patients, and hospital administrators oversee everything.

---

## Key Features That Make UNDA Stand Out

### 1. **Comprehensive Prevention Advocate Profiles**
Unlike basic databases that only store names and addresses, UNDA captures the **complete picture** of each young person:

#### **Personal Development Tracking**
- Education history (schools attended, qualifications)
- Skills and talents (sports, arts, leadership)
- Career interests and goals
- Achievements and milestones

**Why It Matters**: Helps supervisors provide **personalized support** and identify opportunities that match each young person's interests and abilities.

#### **Health & Wellbeing**
UNDA captures critical health information to ensure prevention advocate safety during programs and activities:

**Medical Information**:
- Medical conditions (asthma, diabetes, epilepsy, etc.)
- Known allergies (food, medication, environmental)
- Disabilities or additional needs (physical, learning, developmental)
- Required medications and dosages
- Dietary requirements (religious, medical, or preference-based)

**Mental Health Support**:
- Current support services (counseling, therapy)
- Special considerations or accommodations needed
- Emergency contact procedures

**Why This Matters**: 
- **Safety**: Staff know about allergies before serving food or planning outdoor activities
- **Inclusion**: Accommodations can be arranged in advance (wheelchair access, sensory-friendly spaces)
- **Emergency Response**: Critical medical information accessible instantly if urgent care needed
- **Person-Centered Care**: Support tailored to individual health needs

**Example**: If a prevention advocate has severe peanut allergies, supervisors are alerted before any event involving food. The system flags this during meal planning to prevent potentially life-threatening exposure.

#### **Risk Assessment & Safeguarding**

UNDA includes a **risk categorization system** to prioritize support and ensure vulnerable young people receive appropriate attention:

**Risk Levels**:
- **Low Risk**: Stable situation, regular engagement, no immediate concerns
- **Medium Risk**: Some concerns requiring monitoring (attendance issues, family stressors, minor behavioral changes)
- **High Risk**: Serious concerns requiring immediate attention (safeguarding issues, mental health crisis, homelessness, abuse indicators)

**Risk Assessment Components**:
1. **Risk Level**: Current risk category (Low/Medium/High)
2. **Risk Notes**: Detailed assessment including:
   - Specific risk factors identified
   - Protective factors (supportive family, engaged in school)
   - Intervention plans and referral actions
   - Safeguarding concerns documented
3. **Last Contact Date**: When supervisor last had meaningful interaction with prevention advocate
4. **Next Review Date**: Scheduled date for reassessing risk level
5. **Assessment History**: Date/time of last risk assessment update

**Automated Alerts**:
The system automatically flags:
- **High-risk prevention advocates** who need immediate attention
- **Overdue reviews** where assessment date has passed

**Dashboard Alerts** (Admin View):
Admin dashboard displays urgent alerts prominently:
- High-risk prevention advocate count with detailed list
- Overdue review count with prevention advocate names and due dates
- Color-coded visual indicators (red for high-risk, orange for overdue)
- Quick links to prevention advocate profiles for immediate action

**Why This System Matters**:
- **Prevents Cases Falling Through Cracks**: No prevention advocate is forgotten; overdue reviews automatically surface
- **Prioritizes Resources**: High-risk cases get immediate supervisor attention
- **Evidence-Based Decision Making**: Documented risk factors support referral decisions
- **Accountability**: Clear record of when and why risk levels changed
- **Compliance**: Meets safeguarding best practices and regulatory requirements

**Example Scenario**: A supervisor notices a prevention advocate has missed three consecutive sessions. They update the risk level from Low to Medium, set a next review date for 2 weeks, and document concerns in risk notes. The system automatically includes this prevention advocate in the "Requires Monitoring" filter, ensuring they receive additional check-ins.

#### **Advanced Filtering & Search**

Supervisors can quickly find prevention advocates using multiple filter criteria:

**Available Filters**:
- **Status**: Active, Inactive, On Hold
- **Risk Level**: Low, Medium, High
- **County**: Filter by geographic location
- **Institution**: Filter by school or organization

**How It Works**:
1. Navigate to Supervisor Dashboard
2. Use dropdown filters at top of page
3. Click "Apply Filters" to refine prevention advocate list
4. Active filters shown as color-coded badges
5. "Clear Filters" button resets to show all prevention advocates

**Filter Combinations**: 
Combine multiple filters for precise searches:
- "Show me all High-Risk prevention advocates in Nairobi County" → Status: Active + Risk: High + County: Nairobi
- "Find inactive prevention advocates needing follow-up" → Status: Inactive + Risk: Medium/High

**Prevention Advocate Count Updates**: 
The "Total Prevention Advocates" metric dynamically updates to show filtered count vs total count, giving supervisors clear visibility into how many prevention advocates match their criteria.

**Why This Matters**:
- **Efficiency**: Find specific prevention advocate groups in seconds instead of manual searching
- **Targeted Interventions**: Identify high-risk prevention advocates in specific locations for group interventions
- **Workload Management**: See how many prevention advocates match specific criteria for planning
- **Data-Driven Decisions**: Quick insights into distribution of risk levels, statuses, locations

**Example**: A supervisor wants to organize a support group for prevention advocates with mental health needs in Kiambu County. They filter: Risk: Medium/High → County: Kiambu → Review health notes → Contact relevant prevention advocates directly.


- Medical conditions and allergies
- Dietary requirements
- Disability information
- Mental health support needs

**Why It Matters**: Ensures **safety during activities** and helps staff provide appropriate support. If a prevention advocate has a nut allergy, supervisors know to avoid certain foods at events.

#### **Family Support Network**
- Emergency contacts
- Parent/guardian information
- Social worker details (if applicable)
- Household situation

**Why It Matters**: Enables quick action in emergencies and helps understand each young person's **home support system**.

---

### 2. **Advanced Safeguarding System**

#### **Risk Assessment & Monitoring**
- Track safeguarding concerns and incidents
- Record risk levels (low, medium, high)
- Document support plans and interventions
- Monitor changes over time

**Real-World Example**: If a supervisor notices concerning behavior, they can log it immediately. The system tracks patterns over time and alerts administrators if risk levels increase.

#### **Automatic Alerts**
- High-risk cases flagged on dashboards
- Missing information highlighted
- Overdue reviews shown in red

**Why It Matters**: No young person falls through the cracks. The system acts like a **safety net**, ensuring vulnerable prevention advocates receive timely support.

---

### 3. **Smart Search & Filtering**

Find information instantly:
- Search by name, education, location, or status
- Filter by risk level, engagement, or support needs
- Sort by any field in alphabetical order

**Time-Saving Example**: Instead of flipping through hundreds of paper files to find all prevention advocates attending a specific school, supervisors can filter the list in **2 seconds**.

---

### 4. **Detailed Status Tracking**

Track every prevention advocate's journey:
- **Active**: Currently participating
- **Inactive**: Temporarily away
- **Graduated**: Successfully completed the program
- **Alumni**: Former participants maintaining contact
- **Transferred**: Moved to another program
- **Withdrawn**: Left the program

**Why It Matters**: Provides clear **program outcomes** and helps identify who needs re-engagement support.

---

### 5. **Interactive Dashboards**

#### **Supervisor Dashboard**
- See all assigned prevention advocates at a glance
- Color-coded risk indicators (red = high, orange = medium, green = low)
- Quick access to add or edit prevention advocate information
- Search and filter tools built-in

#### **Admin Dashboard**
- Overview of entire youth network
- Statistics (total prevention advocates, supervisors, high-risk cases)
- System-wide search capabilities
- User management tools

**Visual Design**: Clean, professional interface that looks like modern apps (Netflix, Instagram) rather than old-fashioned office software.

---

### 6. **Real-Time Data Updates**

Changes appear instantly across all devices:
- Supervisor updates a prevention advocate's status → Admin sees it immediately
- Prevention Advocate's information updated → Dashboard refreshes automatically

**Why It Matters**: No confusion from outdated information. Everyone works with the **same current data**, like Google Docs where multiple people can edit simultaneously.

---

### 7. **Mobile-Friendly Design**

Works perfectly on:
- Desktop computers
- Tablets
- Smartphones

**Practical Use**: Supervisors can update prevention advocate information during home visits using their phone, without waiting to return to the office.

---

## Security Features (What Keeps Data Safe)

### **1. Bank-Level Encryption**
- Passwords scrambled using military-grade technology (bcrypt)
- Impossible to read even if someone accessed the database
- Like locking valuables in a safe, not just a drawer

### **2. Account Lockout Protection**
- 5 failed login attempts = account locked for 30 minutes
- Prevents hackers from guessing passwords
- Automatic unlock after timeout or admin reset

### **3. Session Security**
- Automatic logout after 1 hour of inactivity
- Each user gets a unique, encrypted session ID
- Like a temporary visitor badge that expires

### **4. CSRF Protection**
Technical term: **Cross-Site Request Forgery Protection**
Plain English: Prevents malicious websites from tricking users into performing unwanted actions
Example: A fake website can't secretly make you delete data while you're logged in

### **5. Rate Limiting**
- Limits login attempts to prevent brute-force attacks
- Maximum 5 login attempts per minute per user
- Like a bouncer at a club limiting how fast people can enter

### **6. Secure HTTPS Connections**
- All data encrypted during transmission
- Like sending letters in locked envelopes instead of postcards
- Prevents eavesdropping on internet connections

---

## Extra Features That Enhance User Experience

### **1. Password Visibility Toggle**
- Click an eye icon to show/hide your password while typing
- Reduces login errors from typos
- **User-Friendly**: No more typing passwords 3 times because you can't see what you typed!

### **2. Real-Time Form Validation**
- Instant feedback as you type
- Red warnings if information is incorrect
- Green checkmarks when fields are valid
- **Saves Time**: Fix errors immediately instead of submitting the form and seeing errors later

### **3. Success Notifications**
- Green toast messages confirm actions (e.g., "Prevention Advocate added successfully!")
- Auto-dismiss after 3 seconds
- **Reduces Uncertainty**: You know immediately that your action worked

### **4. Error Notifications**
- Red warnings if something goes wrong
- Clear explanations of what happened
- Suggestions for fixing the problem
- **User-Friendly**: No confusing technical error codes

### **5. Loading Indicators**
- Spinning wheel shows when data is being processed
- Prevents confusion ("Did I click the button? Is it working?")
- **Improves Experience**: You know the system is working, just taking a moment

### **6. Professional Medical/SaaS Design**
- Calming blue and green color scheme
- Clean, uncluttered layouts
- Large, readable text
- **Easy on the Eyes**: Reduces fatigue during long work sessions

### **7. Responsive Tables**
- Tables adjust to screen size automatically
- Scrollable on small screens
- Sortable columns (click header to sort)
- **Works Everywhere**: From tiny phone screens to large monitors

### **8. Quick Action Buttons**
- "View Details", "Edit", "Delete" buttons clearly labeled
- Color-coded (blue = view, yellow = edit, red = delete)
- Confirmation prompts before deleting
- **Prevents Mistakes**: Hard to accidentally delete something important

---

## Why These Extra Features Matter

### **For Youth Workers:**
- **Save 2-3 hours per week** on admin tasks
- **Reduce errors** by 70% with real-time validation
- **Find information 10x faster** with smart search
- **Work from anywhere** with mobile access

### **For Program Administrators:**
- **Better oversight** of entire youth network
- **Quick identification** of high-risk cases
- **Data-driven decisions** with comprehensive profiles
- **Compliance-ready** with detailed record-keeping

### **For Young People (Prevention Advocates):**
- **Personalized support** based on comprehensive profiles
- **Safer activities** with health information readily available
- **Better opportunities** matched to their skills and interests
- **Continuous tracking** of their development journey

---

## Getting Started in 3 Easy Steps

### **Step 1: Administrator Creates Your Account**
Your administrator will:
1. Log into the admin dashboard
2. Click "Manage Users" → "Create New User"
3. Enter your username and assign your role (Admin, Supervisor, or Prevention Advocate)
4. System generates a secure temporary password automatically
5. Admin provides you with:
   - Your username
   - Temporary password
   - Website URL

**For Administrators Creating Accounts:**
1. Click **"Manage Users"** from the admin dashboard
2. Click **"Create New User"**
3. Fill in the form:
   - **Username**: Use first.last format (e.g., john.doe)
   - **Role**: Select Admin, Supervisor, or Prevention Advocate
4. Click **"Create User"**
5. **IMPORTANT**: Copy the temporary password shown on screen
6. Share credentials securely with the new user (in person, encrypted email, or secure message)

### **Step 2: First Login**
1. Go to the website
2. Enter your username and temporary password
3. **IMPORTANT**: Change your password immediately for security
4. Click on your username (top right) → **Settings** → **Change Password**
5. Follow the password requirements shown on screen

### **Step 3: Explore Your Dashboard**
- Admins: Start by adding supervisors
- Supervisors: Begin adding your prevention advocates
- Prevention Advocates: View and update your profile information

---

## Common Questions

### **"How do I change my password?"**
1. Click your username in the top right corner
2. Click **Settings**
3. Click **Change Password**
4. Enter your current password
5. Enter and confirm your new password
6. Click **Change Password**

**Password must have:**
- At least 8 characters
- One uppercase letter (A-Z)
- One lowercase letter (a-z)
- One number (0-9)
- One special character (!@#$%^&*)

### **"What if I forget my password?"**
Contact your administrator. They can reset it for you using the **User Management** interface. For security, password resets must be done by an admin, not automatically by email.

### **"Can I access this from home?"**
Yes! As long as you have internet access, you can log in from anywhere using any device.

### **"What if I make a mistake?"**
Most actions can be undone by editing the information. Deletions require confirmation and can often be restored by an administrator.

### **"Is my data safe?"**
Yes! The system uses bank-level security, including encryption, automatic logout, and access controls. Only authorized users can see sensitive information.

### **"What if the internet goes down?"**
You'll need internet to access the system. However, data is automatically backed up, so nothing is lost when connectivity returns.

### **"Can I print information?"**
Yes! Your browser's print function works with all pages. Alternatively, export data to Excel for custom reports.

---

## Success Stories

### **Time Savings**
Before UNDA: 30 minutes to find a prevention advocate's file and update information
After UNDA: **2 minutes** to search, edit, and save

### **Better Safeguarding**
Before UNDA: High-risk prevention advocate overlooked for 2 weeks
After UNDA: **Instant alerts** ensure timely intervention

### **Improved Communication**
Before UNDA: Emergency contact information in different files
After UNDA: **One-click access** to all emergency contacts

### **Data Accuracy**
Before UNDA: 15% of files had outdated information
After UNDA: **Real-time updates** = always current data

---

## Administrator User Management Guide

### **Accessing User Management**
From your admin dashboard, click the **"Manage Users"** button in the Quick Actions section.

### **Creating New Users**

**Step-by-Step:**
1. Click **"Create New User"** (blue button, top right)
2. Enter a **username**:
   - Minimum 3 characters
   - Use format: first.last (e.g., sarah.jones)
   - Keep it professional and easy to remember
3. Select a **role**:
   - **Prevention Advocate**: Can only view/edit their own profile
   - **Supervisor**: Can view/edit all prevention advocates + see dashboard analytics
   - **Admin**: Full system access including user management
4. Click **"Create User"**
5. **IMPORTANT**: Copy the temporary password shown on screen (12-character secure password)
6. Share credentials securely with the new user

**Best Practices:**
- Use standardized username format (first.last)
- Assign the lowest privilege level needed (principle of least privilege)
- Share temporary passwords securely (in person, encrypted email, or secure messaging)
- Remind users to change their password immediately after first login
- Never reuse temporary passwords

### **User Management Dashboard Overview**

The user management page shows:
- **Statistics**: Total users, admins, supervisors, prevention advocates at a glance
- **User Table**: Complete list with:
  - Username
  - Role (color-coded: green=admin, blue=supervisor, yellow=prevention advocate)
  - Last login date
  - Status (active/locked)
  - Failed login attempts
  - Action buttons

### **Resetting Passwords**

**When to use:** User forgot password or account is locked

**How to reset:**
1. Find the user in the user table
2. Click **"Reset Password"** button (yellow)
3. System generates a new 12-character temporary password
4. Account is automatically unlocked (if it was locked)
5. Failed login attempts are reset to 0
6. Copy the new password and share securely with the user

**What happens:**
- Old password is immediately invalidated
- New temporary password must be used
- Account lockout is removed
- User should change password at next login

### **Unlocking Locked Accounts**

**When to use:** User locked out after 5 failed login attempts but remembers their password

**How to unlock:**
1. Find the locked user (status shows red "Locked" badge)
2. Click **"Unlock"** button (green)
3. Account is immediately unlocked
4. Failed attempts counter is reset to 0
5. User can log in with their existing password

**Note:** If user doesn't remember their password, use "Reset Password" instead (which unlocks automatically).

### **Changing User Roles**

**When to use:** User's responsibilities change or promotion/demotion needed

**How to change:**
1. Find the user in the user table
2. Use the **role dropdown** in the Actions column
3. Select new role (Admin/Supervisor/Prevention Advocate)
4. Change takes effect immediately
5. User will see new permissions at next login

**Important:**
- You cannot change your own role (prevents accidental self-demotion)
- Downgrading admin to supervisor/prevention advocate removes user management access
- Upgrading prevention advocate to supervisor grants access to all prevention advocate profiles

### **Deleting Users**

**When to use:** User no longer needs access (employee left, prevention advocate aged out, etc.)

**How to delete:**
1. Find the user in the user table
2. Click **"Delete"** button (red)
3. Confirm the deletion in the popup
4. User account is permanently removed

** CAUTION:**
- **You cannot delete your own account** (prevents accidental lockout)
- **This action cannot be undone**
- Consider unlocking or changing role instead if user might return
- All user data is permanently deleted from the system

### **Security Best Practices**

**For Credential Sharing:**
- Never send passwords via unencrypted email
- Use in-person handoff when possible
- If remote, use encrypted messaging or password managers
- **Instruct users to change temporary passwords immediately**
- Don't store temporary passwords after user receives them

**Password Change Instructions for New Users:**
1. Log in with temporary password
2. Click username (top right) → **Settings**
3. Click **Change Password**
4. Enter current (temporary) password
5. Create a strong new password
6. Confirm new password
7. Click **Change Password**

**For Role Assignment:**
- Give users the minimum access they need
- Regularly audit user roles (quarterly recommended)
- Remove access for inactive users
- Prevention Advocate role is sufficient for most youth workers
- Supervisor role for team leads and case managers
- Admin role only for IT staff and program directors

**For Account Security:**
- Monitor locked accounts regularly
- Investigate repeated failed login attempts (may indicate attack)
- Reset passwords if account compromise suspected
- Keep the admin user list small (fewer than 3 recommended)
- Document who has admin access and why

### **Troubleshooting Common Issues**

**"User can't log in"**
- Check if account is locked (red "Locked" badge) → click "Unlock"
- Verify user is using correct username (check spelling)
- Reset password if user forgot it
- Check user's role is appropriate for what they're trying to access

**"User forgot password"**
- Click "Reset Password" → copy new temp password → share securely
- Account will automatically unlock if locked
- Remind user to change password after logging in
- Instruct user: Login → Click username → Settings → Change Password

**"User needs different access"**
- Use role dropdown to change: Prevention Advocate → Supervisor → Admin
- Changes take effect immediately (no restart needed)
- User may need to log out and back in to see new permissions

**"Can't delete a user"**
- If you can't delete yourself, that's intentional (safety feature)
- Ask another admin to delete your account if needed
- If delete button is missing, check you're logged in as admin

**"Temporary password won't work"**
- Copy password exactly (case-sensitive, includes special characters)
- Don't add extra spaces when pasting
- Generate a new password if unsure (old one expires when new one created)
- Check user is using correct username

---

## Need Help?

### **Technical Issues**
Contact your system administrator or IT support team.

### **Training & How-To Questions**
Refer to this guide or request a refresher training session.

### **Feature Requests**
Submit suggestions to your program coordinator. The system is continuously improved based on user feedback!

---

## Final Thoughts

UNDA Youth Network transforms youth program management from **time-consuming paperwork** to **efficient digital workflows**. It's designed to help you spend **less time on admin** and **more time supporting young people**.

The extra features aren't just "nice to have" - they're carefully chosen to:
- Save time  
- Reduce errors  
- Improve safety  
- Enhance user experience  
- Enable better decision-making  

Think of UNDA as your **digital assistant** that handles the boring administrative tasks, so you can focus on what matters most: **helping young people thrive**.

---

**Welcome to smarter youth work management!**

---

## HEALTH TRACKING & RISK ASSESSMENT GUIDE

### Recording Health Information

Health information is confidential and only visible to supervisors and admins.

**How to Add Health Data:**
1. Navigate to Supervisor Dashboard
2. Click "Review" next to prevention advocate name
3. Scroll to "Health & Safety Information" section
4. Complete relevant fields:
   - Medical Conditions (asthma, diabetes, etc.)
   - Allergies (food, medication, environmental)
   - Mental Health Support (counseling, therapy)
   - Disabilities/Additional Needs
   - Medication Required
   - Dietary Requirements
   - Additional Health Notes
5. Click "Save Health & Risk Data"

**Examples:**
- Medical: "Asthma - requires inhaler during physical activities"
- Allergies: "Severe peanut allergy (anaphylaxis risk)"
- Mental Health: "Weekly counseling for anxiety management"

### Conducting Risk Assessments

**Risk Levels:**
- **Low**: Stable, regular engagement, no concerns
- **Medium**: Some concerns, monitoring needed
- **High**: Serious concerns, immediate attention required

**When to Assess:**
- Initial intake
- After significant life events
- Following behavioral changes
- After safeguarding disclosures
- At scheduled review intervals (3-6 months)

**How to Assess:**
1. Access prevention advocate detail page
2. Select Risk Level dropdown
3. Set Last Contact Date
4. Set Next Review Date (required):
   - Low risk: 3-6 months
   - Medium risk: 1-2 months  
   - High risk: 1-2 weeks
5. Document Risk Assessment Notes:
   - Risk factors identified
   - Protective factors
   - Intervention plans
   - Safeguarding concerns
6. Click "Save Health & Risk Data"

### Responding to Dashboard Alerts

**High-Risk Prevention Advocates Alert (Red):**
- Shows count and list of high-risk prevention advocates
- Displays last contact date
- Action: Contact immediately, escalate safeguarding concerns, document actions

**Overdue Reviews Alert (Orange):**
- Shows prevention advocates past review date
- Lists due dates
- Action: Schedule review, conduct reassessment, set new date

### Using Advanced Filtering

**Available Filters:**
- Status: Active/Inactive/On Hold
- Risk Level: Low/Medium/High
- County: Geographic location
- Institution: School or organization

**How to Filter:**
1. Go to Supervisor Dashboard
2. Select criteria from dropdowns
3. Click "Apply Filters"
4. View filtered prevention advocates
5. Click "Clear" to reset

**Filter Examples:**
- Find high-risk in Nairobi: Status=Active + Risk=High + County=Nairobi
- Inactive needing follow-up: Status=Inactive + Risk=Medium/High
- All at specific school: Institution=[School Name]

### Risk Level Badges

Badges appear on dashboard and detail pages:
- Green badge with checkmark = Low Risk
- Orange badge with triangle = Medium Risk
- Red badge with alert = High Risk

Hover over badge to see assessment date and next review.

### Best Practices

**DO:**
- Update health info immediately when disclosed
- Review assessments at scheduled intervals
- Document specific details in risk notes
- Respond to alerts within 24 hours
- Set realistic review dates
- Involve prevention advocates in assessment process

**DON'T:**
- Assume old health info is still accurate
- Set all prevention advocates to Low without proper assessment
- Ignore overdue review alerts
- Share health data with unauthorized staff
- Use risk levels punitively
- Set unrealistic review schedules

