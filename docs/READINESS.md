# Community release readiness

Assessment date:2026-10-02. The original prototype had no community SRS or release plan. This release adds REQUIREMENTS.md and PLAN.md to record the requested distribution scope and verification bar. It targets the existing Mac workflow; broader platform/store certification is deferred.

Requirements coverage: FR-1 through FR-10 and NFR-1 through NFR-6 are implemented and covered by the checks listed in VERIFICATION.md. Must:14/14 verified; committed Should:2/2 verified. No uncovered Must or known critical/high defect remains. FR-1/FR-2 rely on prior real Helium workflow evidence plus current component checks; Chrome's separate live seller-account test remains outside the certified browser evidence.

Plan phases: clean public tree, reusable installation, printing/recovery hardening, automated/security/performance/independent checks, and reference hardware submission are complete. Final publication requires hosted CI to pass on the public commit before the tag and source-only ZIP are released.

**Pilot: READY** within the documented macOS/Helium/compatible Munbyn/US-address scope.

**Community source release: READY subject to green hosted CI at publication.** This is the production bar for the scoped source distribution, not a claim of Chrome Web Store approval, notarization, all-model printer certification, or Windows support. GitHub's tagged release and successful Actions run provide the final publication record.

Residual limitations are visible in README, INSTALL, SECURITY, PRIVACY and VERIFICATION. Users must complete normal unpacked-extension loading, supply their own return address and compatible driver, verify paper/readability, and inspect uncertain jobs before explicit recovery. No agent or AI service is required during normal use.
