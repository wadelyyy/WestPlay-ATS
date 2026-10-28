//! Names for shared frame textures outlive individual host runs: the plugin may still hold an old texture.
//! All host runs and pipeline rebuilds in this process therefore share one allocation sequence.

use std::sync::LazyLock;
use std::sync::atomic::{AtomicU64, Ordering};

// Preserve a process-dependent starting point without reserving only eight bits for rebuilds.
static GENERATIONS: LazyLock<Generations> = LazyLock::new(|| Generations::new(std::process::id().rotate_left(8)));

pub(super) fn next() -> std::io::Result<u32> {
    GENERATIONS.next().ok_or_else(|| std::io::Error::other("shared frame texture generations exhausted"))
}

/// Every nonzero u32 is available once. Exhaustion fails instead of reusing a name the plugin may hold.
struct Generations {
    seed: u64,
    issued: AtomicU64,
}

impl Generations {
    const COUNT: u64 = u32::MAX as u64;

    fn new(seed: u32) -> Self {
        Self { seed: u64::from(seed), issued: AtomicU64::new(0) }
    }

    fn next(&self) -> Option<u32> {
        let mut issued = self.issued.load(Ordering::Relaxed);
        loop {
            if issued >= Self::COUNT {
                return None;
            }
            match self.issued.compare_exchange_weak(issued, issued + 1, Ordering::Relaxed, Ordering::Relaxed) {
                Ok(ordinal) => return Some(((self.seed + ordinal) % Self::COUNT + 1) as u32),
                Err(current) => issued = current,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeSet;
    use std::sync::Arc;

    use super::*;

    #[test]
    fn successive_host_runs_do_not_reopen_the_previous_runs_texture() {
        // Host run() has no allocator to reset: both runs use the same production static.
        let run = || (0..3).map(|_| next().unwrap()).collect::<Vec<_>>();
        let first_run = run();
        let second_run = run();
        let all: BTreeSet<_> = first_run.iter().chain(&second_run).copied().collect();
        assert_eq!(all.len(), 6);
        assert!(!all.contains(&0));
    }

    #[test]
    fn rebuilds_do_not_repeat_after_the_old_eight_bit_limit() {
        let generations = Generations::new(10_408 << 8);
        let values: Vec<_> = (0..1025).map(|_| generations.next().unwrap()).collect();
        assert_ne!(values[0], values[256]);
        assert_eq!(values.iter().copied().collect::<BTreeSet<_>>().len(), values.len());
        assert!(!values.contains(&0));
    }

    #[test]
    fn crossing_the_numeric_end_skips_zero_without_repeating_a_name() {
        let generations = Generations::new(u32::MAX - 1);
        assert_eq!(generations.next(), Some(u32::MAX));
        assert_eq!(generations.next(), Some(1));
        assert_eq!(generations.next(), Some(2));
    }

    #[test]
    fn an_exhausted_allocator_does_not_wrap_back_to_an_existing_name() {
        let generations = Generations { seed: 0, issued: AtomicU64::new(Generations::COUNT - 1) };
        assert_eq!(generations.next(), Some(u32::MAX));
        assert_eq!(generations.next(), None);
        assert_eq!(generations.next(), None);
    }

    #[test]
    fn concurrent_host_work_cannot_allocate_the_same_name() {
        let generations = Arc::new(Generations::new(10_408 << 8));
        let workers: Vec<_> = (0..4)
            .map(|_| {
                let generations = generations.clone();
                std::thread::spawn(move || (0..256).map(|_| generations.next().unwrap()).collect::<Vec<_>>())
            })
            .collect();
        let values: BTreeSet<_> = workers.into_iter().flat_map(|worker| worker.join().unwrap()).collect();
        assert_eq!(values.len(), 1024);
        assert!(!values.contains(&0));
    }
}
