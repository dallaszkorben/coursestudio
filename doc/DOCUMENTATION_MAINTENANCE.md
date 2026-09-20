# Documentation Maintenance Guidelines

**CRITICAL RULE: Always Keep Documentation Synchronized**

---

## 🚨 PRIMARY RULE

**WHENEVER YOU:**
- Learn something new about the system
- Change an existing implementation
- Discover a new requirement
- Fix a bug that affects design
- Change a decision or approach
- Update code structure
- Modify configuration system
- Adjust any specification

**YOU MUST:**
- Update ALL related documentation immediately
- Do NOT proceed with next task without updating docs
- Check all related files that might be affected
- Verify cross-references are still correct

---

## 📋 DOCUMENTATION FILES & THEIR PURPOSE

### Core Specification Documents

**PROJECT_SPECIFICATION.md**
- Master specification document
- Contains all functional requirements
- Technical requirements
- UI specifications
- Garmin compatibility requirements
- Update when: Any requirement changes, new features, spec clarifications

**ARCHITECTURE.md**
- System design and data flow
- Class hierarchy
- Signal/slot connections
- Data structures
- Performance considerations
- Update when: Design patterns change, new classes added, data flow modified

**TODO_LIST.md**
- Step-by-step development tasks
- Each step's objectives, tasks, acceptance criteria
- Progress tracking table
- Update when: Steps completed, tasks change, new dependencies discovered

### Reference Documents

**PROJECT_SUMMARY.md**
- Quick reference guide
- Key decisions
- Configuration reference
- Development workflow
- Update when: Key decisions change, config structure modified

**README.md**
- Documentation index
- Navigation guide
- Document relationships
- Update when: New documents added, structure reorganized

**IMPLEMENTATION_NOTES.md** (To be created)
- Design decisions and rationale
- Lessons learned
- Technical discoveries
- Deviations from specification
- Update when: Major decisions made, new patterns discovered, pitfalls avoided

---

## 🔄 CROSS-REFERENCE MATRIX

When you change something, check these related documents:

### Change in PROJECT_SPECIFICATION.md
→ Update: ARCHITECTURE.md, TODO_LIST.md, PROJECT_SUMMARY.md, IMPLEMENTATION_NOTES.md

### Change in ARCHITECTURE.md
→ Update: PROJECT_SPECIFICATION.md, TODO_LIST.md, IMPLEMENTATION_NOTES.md

### Change in code structure or classes
→ Update: ARCHITECTURE.md (class diagram), TODO_LIST.md (dependencies)

### Change in configuration system
→ Update: PROJECT_SPECIFICATION.md section 4, PROJECT_SUMMARY.md, settings.ini documentation

### Change in Garmin compatibility requirements
→ Update: PROJECT_SPECIFICATION.md section 5, garmin-gpx-processing-guide.md, IMPLEMENTATION_NOTES.md

### Change in coordinate format handling
→ Update: PROJECT_SPECIFICATION.md section 6, ARCHITECTURE.md section 5, TODO_LIST.md step 3

### Change in UI layout
→ Update: PROJECT_SPECIFICATION.md section 7, ARCHITECTURE.md section 1, TODO_LIST.md steps 5, 6-10

### Change in undo/redo system
→ Update: PROJECT_SPECIFICATION.md section 2.6, ARCHITECTURE.md section 4, TODO_LIST.md steps 15-17

### Completion of a TODO step
→ Update: TODO_LIST.md progress table, IMPLEMENTATION_NOTES.md with findings

---

## ✅ DOCUMENTATION UPDATE CHECKLIST

**Before moving to the next task, ask yourself:**

- [ ] Did I learn something new? → Document it in IMPLEMENTATION_NOTES.md
- [ ] Did I change the design? → Update ARCHITECTURE.md
- [ ] Did I change requirements? → Update PROJECT_SPECIFICATION.md
- [ ] Did I complete a step? → Mark it in TODO_LIST.md progress table
- [ ] Did I discover a pitfall? → Add to IMPLEMENTATION_NOTES.md Lessons Learned
- [ ] Did I change configuration? → Update PROJECT_SUMMARY.md and settings.ini docs
- [ ] Are there cross-references I need to verify? → Check all related docs
- [ ] Is the documentation accurate to current state? → Compare with code

---

## 📝 DOCUMENTATION UPDATE TEMPLATE

When you discover something new, document it using this format:

```markdown
### [Date] - [What Changed]

**What Changed:**
- Brief description of the change

**Why:**
- Reason for the change
- Problem it solves
- Context

**Updated Files:**
- File 1: Changes made
- File 2: Changes made
- File 3: Changes made

**Related Sections:**
- Link to affected specification sections
- Link to related TODO steps
- Link to related architecture diagrams

**Testing Notes:**
- How it was tested
- Any edge cases discovered
- Performance implications if any

**Next Steps if Any:**
- Follow-up actions needed
- Remaining work related to this change
```

---

## 🎯 SPECIFIC DOCUMENTATION RULES

### Rule 1: Configuration Changes
**If you change configuration system:**
1. Update PROJECT_SPECIFICATION.md section 4 (Configuration Management)
2. Update PROJECT_SUMMARY.md Configuration section
3. Update settings.ini with new options
4. Add to IMPLEMENTATION_NOTES.md with date and rationale
5. Check TODO_LIST.md if dependencies changed

### Rule 2: New Classes or Modules
**If you add a new class or module:**
1. Add to ARCHITECTURE.md class hierarchy section
2. Update PROJECT_SPECIFICATION.md if it affects spec
3. Update TODO_LIST.md if dependencies changed
4. Add to IMPLEMENTATION_NOTES.md with design rationale

### Rule 3: Bug Fixes or Design Changes
**If you discover and fix an issue:**
1. Document in IMPLEMENTATION_NOTES.md under "Issues Resolved"
2. Update affected specification/architecture sections
3. Update TODO_LIST.md if acceptance criteria affected
4. Add testing notes to prevent regression

### Rule 4: Coordinate Format Discovery
**If you learn something new about coordinate conversion:**
1. Update PROJECT_SPECIFICATION.md section 6
2. Update ARCHITECTURE.md section 5 (data structures)
3. Add examples to IMPLEMENTATION_NOTES.md
4. Update TODO_LIST.md Step 3 if needed

### Rule 5: Garmin Compatibility Discovery
**If you discover Garmin requirement changes:**
1. Update PROJECT_SPECIFICATION.md section 5
2. Update garmin-gpx-processing-guide.md
3. Update ARCHITECTURE.md if architecture affected
4. Add to IMPLEMENTATION_NOTES.md with date
5. Update TODO_LIST.md steps 18-19 if needed

---

## 📊 DOCUMENTATION MAINTENANCE LOG

Use this section to track documentation updates:

| Date | Change Type | Files Updated | Reason | Step |
|------|-------------|---|---|---|
| 2026-09-20 | Rule added | DOCUMENTATION_MAINTENANCE.md | Critical reminder system | Planning |
| | | | | |

---

## 🔍 VERIFICATION PROCESS

**Before committing to the next step, verify:**

1. **Consistency Check:**
   - All cross-references are correct
   - Version numbers match (if applicable)
   - File paths are accurate
   - URLs/links work (if any)

2. **Completeness Check:**
   - All scenarios covered
   - Edge cases documented
   - Examples are accurate
   - No placeholder text remaining

3. **Accuracy Check:**
   - Specification matches implementation
   - Architecture matches code
   - TODO steps match current state
   - No contradictory statements

4. **Clarity Check:**
   - Technical terms defined
   - Acronyms explained on first use
   - Examples clear and correct
   - Instructions unambiguous

---

## 🚫 DOCUMENTATION ANTI-PATTERNS

**Avoid these mistakes:**

❌ **Update code but forget documentation**
→ Always update docs when code changes

❌ **Update one document but miss related documents**
→ Check cross-reference matrix

❌ **Add new requirements without updating spec**
→ Always trace through all related docs

❌ **Leave placeholder text or TODO comments**
→ Complete documentation before moving on

❌ **Update documentation but don't commit the changes**
→ Documentation updates are part of task completion

❌ **Guess at information instead of verifying**
→ Check the code, test it, then document findings

❌ **Create inconsistent terminology**
→ Use consistent terms across all documents

---

## 📌 DOCUMENTATION PRIORITIES

**Update immediately (same task):**
1. Acceptance criteria changes
2. Specification changes
3. Architecture changes
4. Configuration changes

**Update before next step:**
1. TODO_LIST.md progress table
2. IMPLEMENTATION_NOTES.md findings
3. Cross-reference verification

**Update end of phase:**
1. Summary documents
2. Performance findings
3. Lessons learned

---

## 🎓 LESSONS LEARNED SECTION (IMPLEMENTATION_NOTES.md)

Every time you learn something, add to this section:

```markdown
## Lessons Learned

### [Date] - [Topic]
**Discovery:** What was learned
**Why it matters:** Impact on project
**How to avoid:** Preventive measures
**References:** Related docs/code
```

---

## ✨ GOLDEN RULE

**Documentation is not separate from development.**

It's part of understanding the problem. As you code and learn, you improve documentation. Documentation should always reflect the current reality of the system.

**If documentation and code disagree, one of them is wrong. Fix both.**

---

**This document was created: 2026-09-20**  
**Last updated: 2026-09-20**  
**Maintained by:** Development team  
**Review frequency:** After each development phase
