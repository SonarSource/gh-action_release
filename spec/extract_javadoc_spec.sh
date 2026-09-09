#!/usr/bin/env bash

Describe 'extract-javadoc.sh single javadoc scenario'

  BeforeEach 'setup_test_dir'
  AfterEach 'cleanup_test_dir'

  setup_test_dir() {
    original_dir=$(pwd)

    # Create a directory that matches the pattern from the workflow: repo.XXXXXXXX
    # Use mktemp to get a temp name, then create it in current dir
    temp_name=$(mktemp -u repo.XXXXXXXX)
    test_dir="$original_dir/$temp_name"
    mkdir -p "$test_dir"
  }

  cleanup_test_dir() {
    cd "$original_dir" || return
    rm -rf "$test_dir"
  }

  # Helper function to create javadoc jar files
  create_javadoc_jar() {
    local jar_name="$1"
    local content_prefix="$2"

    echo "${content_prefix} javadoc content" > index.html
    echo "${content_prefix} package info" > package-summary.html
    zip -q "$jar_name" index.html package-summary.html
    rm index.html package-summary.html
  }

  Describe 'single javadoc file extraction'
    It 'should extract single javadoc file to versioned directory'
      cd "$test_dir" || return

      create_javadoc_jar "sonar-plugin-api-13.0.0.3026-javadoc.jar" "dummy"

       When call "$original_dir/scripts/extract-javadoc.sh" "$test_dir" "13.0.0.3026"

      The status should be success
      The stdout should include "Found single javadoc file, using simple extraction"

      The directory "javadoc/13.0.0.3026" should be exist
      The file "javadoc/13.0.0.3026/index.html" should be exist
    End

    It 'should select main javadoc when test/fixture variants exist'
      cd "$test_dir" || return

      create_javadoc_jar "sonar-plugin-api-13.0.0.3026-javadoc.jar" "main"

      create_javadoc_jar "sonar-plugin-api-test-fixtures-13.0.0.3026-javadoc.jar" "test"

      When call "$original_dir/scripts/extract-javadoc.sh" "$test_dir" "13.0.0.3026"

      The status should be success
      The stdout should include "Found multiple javadoc files:"
      The stdout should include "Found single main javadoc file (plus test/fixture noise), using simple extraction"

      The directory "javadoc/13.0.0.3026" should be exist
      The file "javadoc/13.0.0.3026/index.html" should be exist
      The contents of file "javadoc/13.0.0.3026/index.html" should include "main"
    End

    It 'should give each real module its own subdirectory (mixed-privacy release)'
      cd "$test_dir" || return

      create_javadoc_jar "sonar-dummy-maven-plugin-16.1.0.3600-javadoc.jar" "public"
      create_javadoc_jar "sonar-dummy-maven-enterprise-plugin-16.1.0.3600-javadoc.jar" "private"

      When call "$original_dir/scripts/extract-javadoc.sh" "$test_dir" "16.1.0.3600" "true"

      The status should be success
      The stdout should include "Found multiple javadoc files:"
      The stdout should include "Extracting 2 javadoc file(s) into their own subdirectories:"

      # A generated landing page, not either module's own (clobbered) index.html.
      The file "javadoc/16.1.0.3600/index.html" should be exist
      The contents of file "javadoc/16.1.0.3600/index.html" should include "sonar-dummy-maven-plugin"
      The contents of file "javadoc/16.1.0.3600/index.html" should include "sonar-dummy-maven-enterprise-plugin"

      # Each module's own root-level files must survive under its own subdirectory, unclobbered.
      The file "javadoc/16.1.0.3600/sonar-dummy-maven-plugin/index.html" should be exist
      The contents of file "javadoc/16.1.0.3600/sonar-dummy-maven-plugin/index.html" should include "public"
      The file "javadoc/16.1.0.3600/sonar-dummy-maven-enterprise-plugin/index.html" should be exist
      The contents of file "javadoc/16.1.0.3600/sonar-dummy-maven-enterprise-plugin/index.html" should include "private"
    End

    It 'should keep first-jar-wins behavior for multiple real modules when not a mixed-privacy release'
      cd "$test_dir" || return

      create_javadoc_jar "sonar-cobol-plugin-16.1.0.3600-javadoc.jar" "cobol-frontend"
      create_javadoc_jar "sonar-cobol-checks-16.1.0.3600-javadoc.jar" "cobol-checks"

      When call "$original_dir/scripts/extract-javadoc.sh" "$test_dir" "16.1.0.3600" "false"

      The status should be success
      The stdout should include "Found multiple javadoc files:"
      The stdout should include "Found multiple main javadoc files but not a mixed-privacy release, using simple extraction on the first one:"

      # Glob order is alphabetical: sonar-cobol-checks sorts before sonar-cobol-plugin.
      The file "javadoc/16.1.0.3600/index.html" should be exist
      The contents of file "javadoc/16.1.0.3600/index.html" should include "cobol-checks"

      # The second module is silently discarded, matching pre-BUILD-12556 behavior.
      The path "javadoc/16.1.0.3600/sonar-cobol-plugin" should not be exist
    End
  End
End
