# 🔍 Code Review Checklist & Template

## 📋 PR Information
**Pull Request Title:** [PR Title]  
**Author:** [AI Agent]  
**Reviewers Required:** 2 AI agents minimum  
**Priority:** [Critical/High/Medium/Low]  
**Related Sprint:** [Sprint Number]  
**Related Tasks:** [Link to task tracking]

---

## ✅ Review Checklist

### 🏗️ Architecture & Design
- [ ] **Code follows established architecture patterns**
- [ ] **Follows SOLID principles and clean code practices**
- [ ] **No unnecessary complexity or over-engineering**
- [ ] **Proper separation of concerns**
- [ ] **Integration points properly defined and documented**

### 🔒 Security Review
- [ ] **No hardcoded secrets or API keys**
- [ ] **Input validation implemented where needed**
- [ ] **Authentication and authorization properly handled**
- [ ] **No SQL injection or XSS vulnerabilities**
- [ ] **Sensitive data properly encrypted/protected**

### ♿ Accessibility Review (Required: Claude Approval)
- [ ] **WCAG 2.1 AA compliance maintained**
- [ ] **Screen reader compatibility preserved**
- [ ] **Keyboard navigation supported**
- [ ] **Voice-only operation not broken**
- [ ] **High contrast mode supported**
- [ ] **No accessibility regressions introduced**

### 🎯 Functionality Review
- [ ] **Code meets acceptance criteria**
- [ ] **Edge cases properly handled**
- [ ] **Error handling implemented**
- [ ] **Performance requirements met**
- [ ] **Memory usage optimized**

### 🧪 Testing Review
- [ ] **Unit tests provided (>80% coverage)**
- [ ] **Integration tests for new features**
- [ ] **All tests passing**
- [ ] **Test cases cover edge scenarios**
- [ ] **Accessibility tests included**

### 📚 Documentation Review
- [ ] **Code properly commented**
- [ ] **API documentation updated**
- [ ] **README updates if needed**
- [ ] **Breaking changes documented**
- [ ] **Task tracking updated**

### 🚀 Performance Review
- [ ] **No performance regressions**
- [ ] **Memory leaks checked**
- [ ] **CPU usage optimized**
- [ ] **Response time requirements met**
- [ ] **Hardware-specific optimizations considered**

---

## 🤖 AI Agent Review Assignments

### Mandatory Reviews
| Review Type | Required Reviewer | Backup Reviewer |
|-------------|-------------------|-----------------|
| **Accessibility** | Claude | GitHub Copilot |
| **Performance** | TabNine AI | Trae AI |
| **Security** | Cursor AI | Claude |
| **Architecture** | Trae AI | Cursor AI |

### Specialized Reviews
| Code Area | Primary Reviewer | Secondary Reviewer |
|-----------|------------------|-------------------|
| **Voice/Audio (STT/TTS)** | GitHub Copilot | Google Gemini |
| **AI/ML Integration** | Google Gemini | Trae AI |
| **Memory Systems** | TabNine AI | Cursor AI |
| **Integration/OAuth** | Cursor AI | TabNine AI |
| **Emergency Systems** | Claude | GitHub Copilot |

---

## 📝 Review Comments Template

### 🔴 Critical Issues (Must Fix)
```markdown
**🔴 CRITICAL:** [Issue description]
**Location:** [File:Line or function name]
**Impact:** [Security/Accessibility/Performance/Functionality]
**Suggested Fix:** [Specific suggestion]
**Blocker:** This must be fixed before merge
```

### 🟡 Important Issues (Should Fix)
```markdown
**🟡 IMPORTANT:** [Issue description]
**Location:** [File:Line or function name]
**Impact:** [Impact description]
**Suggested Fix:** [Specific suggestion]
**Priority:** High/Medium
```

### 🔵 Suggestions (Nice to Have)
```markdown
**🔵 SUGGESTION:** [Improvement suggestion]
**Location:** [File:Line or function name]
**Benefit:** [Benefit description]
**Optional:** Can be addressed in future PR
```

### ✅ Positive Feedback
```markdown
**✅ EXCELLENT:** [What was done well]
**Location:** [File:Line or function name]
**Why:** [Explanation of why this is good]
```

---

## 🎯 Review Workflow

### Step 1: Initial Review Assignment
1. **Author creates PR** with proper title and description
2. **System assigns 2+ reviewers** based on code area
3. **Mandatory reviewers assigned** (Claude for accessibility, etc.)

### Step 2: Review Process
1. **Reviewers have 24 hours** to complete review
2. **Use review template** and checklist above
3. **Provide specific, actionable feedback**
4. **Test changes if possible**

### Step 3: Feedback & Iteration
1. **Author addresses feedback** and requests re-review
2. **Reviewers verify fixes** and approve/request changes
3. **All required approvals** must be obtained before merge

### Step 4: Final Approval
1. **Minimum 2 approvals** required (including mandatory reviewers)
2. **All CI/CD checks** must pass
3. **No unresolved critical issues**
4. **Merge authorized** by Trae AI (coordinator)

---

## 🚨 Emergency Review Process

### When to Use
- **Critical bug fixes**
- **Security vulnerabilities**
- **Accessibility blockers**
- **System-down scenarios**

### Emergency Workflow
1. **Mark PR as EMERGENCY**
2. **Immediate review** by available agents
3. **Fast-track approval** (1 review minimum, but prefer 2)
4. **Post-merge review** within 24 hours
5. **Follow-up PR** if additional issues found

---

## 📊 Review Metrics & Quality

### Review Quality Metrics
- **Review completion time:** <24 hours target
- **Issue detection rate:** Track critical issues found
- **False positive rate:** Track incorrect feedback
- **Review thoroughness:** Coverage of checklist items

### Code Quality Metrics
- **Post-merge bugs:** <5% of reviewed code
- **Performance impact:** No degradation
- **Accessibility compliance:** 100% maintained
- **Security vulnerabilities:** 0 tolerance

### Reviewer Performance
- **Response time:** Track reviewer response times
- **Quality feedback:** Track helpful vs unhelpful comments
- **Knowledge sharing:** Encourage learning comments
- **Collaboration:** Track cross-agent assistance

---

## 🎓 Review Best Practices

### For Authors
1. **Self-review first** before requesting reviews
2. **Provide clear PR description** with context
3. **Include test results** and performance data
4. **Respond promptly** to reviewer feedback
5. **Ask for help** if feedback is unclear

### For Reviewers
1. **Be constructive** and specific in feedback
2. **Provide examples** and alternatives
3. **Test the changes** when possible
4. **Share knowledge** and explain reasoning
5. **Approve quickly** when requirements are met

### For All Agents
1. **Maintain professionalism** and respect
2. **Focus on code quality** not personal preferences
3. **Help each other learn** through reviews
4. **Escalate blocking issues** quickly
5. **Celebrate good code** and improvements

---

*Code Review Process v1.0 | Created: December 2024*