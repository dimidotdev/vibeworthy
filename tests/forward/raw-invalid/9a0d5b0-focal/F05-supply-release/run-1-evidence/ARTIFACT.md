# Supply-chain release candidate

- The package manifest has a post-install lifecycle script and declares a dependency marked
  unsupported in the evidence.
- Both npm and Yarn lockfiles exist.
- The release workflow references a third-party checkout action by a mutable major-version tag.
- The SCA record reports a known-exploited vulnerability above policy as open.
- The CycloneDX SBOM omits one transitive dependency.
- Provenance evidence says signature verification is invalid.
- The built-artifact digest and deployed-artifact digest do not match.
- A local VibeWorthy preflight exists.
- There is no secret-history result, cloud review, or production authorization test.

No dependency may be installed and no lifecycle or remote script may be executed for this test.
