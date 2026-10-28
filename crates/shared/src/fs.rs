//! Publishing completed files without reading or copying a partially written replacement.

use std::io;
use std::path::Path;

/// Moves a completed temporary file to its final name, replacing an existing file whole.
///
/// Uses `std::fs::rename` first. An MSIX application's logical AppData namespace can map to a
/// different physical volume: Windows then reports `ERROR_NOT_SAME_DEVICE` (17) even for files
/// written in the same logical directory. For that error alone, retry with the existing source's
/// canonical path and the canonical target parent plus its filename. The target need not exist.
/// Both attempts are renames; this never falls back to a non-atomic copy-and-delete operation.
///
/// # Errors
/// Returns the original rename error unless it is Windows error 17 and both paths can be resolved.
/// In that case, returns the result of the canonical-path rename. Genuine cross-volume moves,
/// permission failures and files held open remain errors. Callers retain their normal cleanup policy.
pub fn replace_file(source: impl AsRef<Path>, target: impl AsRef<Path>) -> io::Result<()> {
    let (source, target) = (source.as_ref(), target.as_ref());
    match std::fs::rename(source, target) {
        Err(error) if cfg!(windows) && error.raw_os_error() == Some(17) => {
            let Some(filename) = target.file_name() else { return Err(error) };
            let parent = target.parent().filter(|path| !path.as_os_str().is_empty()).unwrap_or(Path::new("."));
            let (Ok(source), Ok(parent)) = (std::fs::canonicalize(source), std::fs::canonicalize(parent)) else {
                return Err(error);
            };
            std::fs::rename(source, parent.join(filename))
        }
        result => result,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn folder(name: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!("westplay-file-publish-{name}-{}", std::process::id()));
        std::fs::create_dir_all(&root).unwrap();
        root
    }

    #[test]
    fn publishes_a_file_whose_final_name_does_not_exist() {
        let root = folder("new");
        let source = root.join("map.json.partial");
        let target = root.join("map.json");
        std::fs::write(&source, b"complete new manifest").unwrap();
        replace_file(&source, &target).unwrap();
        assert_eq!(std::fs::read(&target).unwrap(), b"complete new manifest");
        assert!(!source.exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn replaces_the_old_file_whole() {
        let root = folder("replace");
        let source = root.join("settings.json.partial");
        let target = root.join("settings.json");
        std::fs::write(&source, b"new settings").unwrap();
        std::fs::write(&target, b"older and longer settings").unwrap();
        replace_file(&source, &target).unwrap();
        assert_eq!(std::fs::read(&target).unwrap(), b"new settings");
        assert!(!source.exists());
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_missing_source_keeps_the_existing_target_and_rename_error() {
        let root = folder("missing-source");
        let source = root.join("missing.partial");
        let target = root.join("settings.json");
        std::fs::write(&target, b"keep these settings").unwrap();
        let expected = std::fs::rename(&source, &target).unwrap_err();
        let actual = replace_file(&source, &target).unwrap_err();
        assert_eq!(actual.raw_os_error(), expected.raw_os_error());
        assert_eq!(std::fs::read(&target).unwrap(), b"keep these settings");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn a_missing_target_directory_keeps_the_partial_and_rename_error() {
        let root = folder("missing-parent");
        let source = root.join("map.json.partial");
        let target = root.join("missing").join("map.json");
        std::fs::write(&source, b"keep this complete manifest").unwrap();
        let expected = std::fs::rename(&source, &target).unwrap_err();
        let actual = replace_file(&source, &target).unwrap_err();
        assert_eq!(actual.raw_os_error(), expected.raw_os_error());
        assert_eq!(std::fs::read(&source).unwrap(), b"keep this complete manifest");
        assert!(!target.exists());
        std::fs::remove_dir_all(root).unwrap();
    }
}
