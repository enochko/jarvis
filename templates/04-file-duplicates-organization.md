# File Organization & Duplicate Detection

## Find Duplicates Across Drives

```
Scan the following directories for duplicate files:
- [PATH_1]
- [PATH_2]
- [PATH_3 e.g., /Volumes/ExternalDrive/...]

Detection method:
- Compare by file content hash (SHA-256), NOT filename
- This catches duplicates even when filenames differ
- Group results by duplicate sets

Filter:
- File types: [all | specific extensions e.g., .mp3 .flac .jpg]
- Minimum size: [e.g., 1MB to skip tiny files]
- Exclude: [e.g., .DS_Store, node_modules, .git]

Output a report to [PATH_TO_REPORT].md with:
- Total files scanned and total duplicates found
- Disk space reclaimable
- Each duplicate group: all file paths, sizes, last modified dates
- Recommendation for which copy to keep (prefer shortest path,
  most recent, or location preference you specify)

DO NOT delete anything. Report only.
```

## Example

```
Scan for duplicate files across:
- ~/Music/Artist/
- /Volumes/MusicBackup/Artist/
- /Volumes/OldDrive/Music/

Detection: SHA-256 content hash (catch renamed duplicates)
File types: .mp3 .flac .m4a .wav .aac
Minimum size: 500KB
Exclude: .DS_Store, Thumbs.db, desktop.ini

Output report to ~/reports/twice-duplicates-report.md with:
- Duplicate groups showing all paths
- File sizes and last modified dates
- Total reclaimable space
- Recommend keeping the copy in ~/Music/Artist/ when possible

DO NOT delete any files. Report only — I'll review and decide.
```

## Important Notes

**Can Claude Code access external drives?**
Yes — Claude Code runs in your terminal with your user permissions. If you can
`ls /Volumes/MyDrive` or `ls /mnt/external`, Claude Code can too.

**Performance considerations:**
- Hashing large drives takes time. For a first pass, Claude can use file size
  as a pre-filter (only hash files with matching sizes).
- For drives with 100K+ files, expect this to run for a while.
- Ask Claude to show progress (e.g., print count every 1000 files).

**Safety:**
- Always use "report only, don't delete" on the first pass
- Review the report before authorizing any deletions
- Consider a "move to trash" approach rather than permanent delete

## Other File Organization Tasks

```
# Organize files by type/date
Scan [PATH] and organize files into subdirectories by:
- [year/month | file type | project | custom rule]
Create a plan showing proposed moves. Don't execute until I approve.

# Find large files
Find the 50 largest files in [PATH] recursively.
Report path, size, last accessed date.

# Check folder structure
Analyze the directory structure of [PATH] (2 levels deep).
Report: total size, file count by type, any obvious organizational issues.
```

## Tips

- Start with a dry-run report before any moves/deletions
- SHA-256 is definitive for content matching regardless of filename
- For music specifically: consider that same song might exist as .mp3 and .flac
  (different content hashes) — mention if you want cross-format detection
- External drives on macOS: `/Volumes/DriveName/`
- External drives on Linux: `/mnt/` or `/media/username/`
- External drives on Windows (WSL): `/mnt/c/`, `/mnt/d/`, etc.
