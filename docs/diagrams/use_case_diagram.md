# Use Case Diagram - AI Tutor App

## Actors
- **Student**: Primary user who learns through the app
- **Teacher**: Optional user who can manage curriculum
- **Admin**: System administrator

## Use Cases

### Student Use Cases
1. **Login**
   - Enter student ID and school code
   - Continue in offline mode
   - Precondition: Student account exists
   - Postcondition: Student authenticated, dashboard displayed

2. **Ask Tutor**
   - Submit question to AI tutor
   - Receive contextual answer with source references
   - Precondition: Student logged in
   - Postcondition: Answer displayed, conversation history updated

3. **Review Flashcards**
   - View due flashcards
   - Rate response quality (1-5)
   - Precondition: Student logged in, cards due
   - Postcondition: SM2 schedule updated

4. **View Dashboard**
   - View streak, due items, retention rate
   - View mastery progress
   - Precondition: Student logged in
   - Postcondition: Progress statistics displayed

5. **Manage Settings**
   - Update student profile
   - Configure review limits
   - Toggle auto-sync
   - Precondition: Student logged in
   - Postcondition: Settings saved

6. **Sync Data**
   - Push local changes to server
   - Pull remote changes
   - Precondition: Internet connection available
   - Postcondition: Data synchronized

### Teacher Use Cases
1. **Upload Curriculum**
   - Upload PDF curriculum files
   - Precondition: Teacher authenticated
   - Postcondition: Corpus updated

2. **Review Student Progress**
   - View student statistics
   - Precondition: Teacher authenticated
   - Postcondition: Progress displayed

### Admin Use Cases
1. **Manage Users**
   - Create/delete student accounts
   - Precondition: Admin authenticated
   - Postcondition: User database updated

2. **Monitor System**
   - View sync logs
   - Check system health
   - Precondition: Admin authenticated
   - Postcondition: System status displayed

## Relationships
- Student **extends** Teacher (teachers can also be students)
- Teacher **includes** Upload Curriculum
- Admin **includes** Manage Users
- Ask Tutor **includes** Sync Data (if online)
- Review Flashcards **includes** Sync Data (if online)
