# Maven Central Sync

This action is designed to release one build of one repository to maven central.
The artifacts need to be signed. This should happen in the build pipeline of long living branches.

## Staging Profile ID
The endpoint `https://s01.oss.sonatype.org/service/local/staging/profiles` will return a xml where you can lookup the IDs for staging profiles.
```xml
<stagingProfiles>
    <data>
        <stagingProfile>
            <id>13c1877339a4cf</id>
            <name>org.sonarsource</name>
            ...
        </stagingProfile>
    </data>
</stagingProfiles>
```