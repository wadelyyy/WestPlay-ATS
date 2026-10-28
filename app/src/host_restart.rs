//! Bounded recovery of a host run. Browser errors, other host errors and panics share one budget.
//! A requested stop or a GPU migration never spends it.

use std::time::{Duration, Instant};

pub(super) const MAX_RESTARTS: usize = 5;
pub(super) const RESTART_WINDOW: Duration = Duration::from_secs(60);
pub(super) const RESTART_DELAY: Duration = Duration::from_secs(1);

pub(super) enum Ended {
    Stopped,
    GpuChanged,
    Failed(String),
}

#[derive(Debug, PartialEq)]
pub(super) enum Next {
    Stop,
    GpuChanged,
    Restart { attempt: usize, error: String },
    Exhausted { error: String },
}

#[derive(Default)]
pub(super) struct RestartPolicy {
    restarts: Vec<Instant>,
}

impl RestartPolicy {
    pub(super) fn after_run(&mut self, ended: Ended, stopping: bool, now: Instant) -> Next {
        if stopping {
            return Next::Stop;
        }
        let error = match ended {
            Ended::Stopped => return Next::Stop,
            Ended::GpuChanged => return Next::GpuChanged,
            Ended::Failed(error) => error,
        };
        self.restarts.retain(|&at| now.saturating_duration_since(at) < RESTART_WINDOW);
        if self.restarts.len() >= MAX_RESTARTS {
            return Next::Exhausted { error };
        }
        self.restarts.push(now);
        Next::Restart { attempt: self.restarts.len(), error }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn failure(error: &str) -> Ended {
        Ended::Failed(error.into())
    }

    #[test]
    fn browser_errors_host_errors_and_panics_share_a_bounded_budget() {
        let mut policy = RestartPolicy::default();
        let now = Instant::now();
        for (index, error) in
            ["browser gone", "host error", "it crashed", "browser gone", "host error"].into_iter().enumerate()
        {
            assert_eq!(
                policy.after_run(failure(error), false, now + Duration::from_secs(index as u64)),
                Next::Restart { attempt: index + 1, error: error.into() }
            );
        }
        assert_eq!(
            policy.after_run(failure("it crashed again"), false, now + Duration::from_secs(5)),
            Next::Exhausted { error: "it crashed again".into() }
        );
    }

    #[test]
    fn the_limit_is_a_rolling_window_and_expires_at_sixty_seconds() {
        let mut policy = RestartPolicy::default();
        let start = Instant::now();
        for seconds in [0, 15, 30, 45, 59] {
            assert!(matches!(
                policy.after_run(failure("failed"), false, start + Duration::from_secs(seconds)),
                Next::Restart { .. }
            ));
        }
        assert!(matches!(
            policy.after_run(failure("too soon"), false, start + Duration::from_secs(59)),
            Next::Exhausted { .. }
        ));
        // Only the first restart has expired; a fixed window resetting all five would allow too many.
        assert_eq!(
            policy.after_run(failure("retry"), false, start + Duration::from_secs(60)),
            Next::Restart { attempt: 5, error: "retry".into() }
        );
        assert!(matches!(
            policy.after_run(failure("too soon"), false, start + Duration::from_secs(61)),
            Next::Exhausted { .. }
        ));
        assert_eq!(
            policy.after_run(failure("after recovery"), false, start + Duration::from_secs(121)),
            Next::Restart { attempt: 1, error: "after recovery".into() }
        );
    }

    #[test]
    fn a_requested_stop_wins_over_failures_and_gpu_changes_without_spending_retries() {
        let mut policy = RestartPolicy::default();
        let now = Instant::now();
        for ended in [failure("browser gone"), failure("it crashed"), Ended::GpuChanged, Ended::Stopped] {
            assert_eq!(policy.after_run(ended, true, now), Next::Stop);
        }
        assert_eq!(
            policy.after_run(failure("failed"), false, now),
            Next::Restart { attempt: 1, error: "failed".into() }
        );
    }

    #[test]
    fn gpu_migrations_and_graceful_stops_do_not_spend_the_failure_budget() {
        let mut policy = RestartPolicy::default();
        let now = Instant::now();
        for _ in 0..MAX_RESTARTS * 2 {
            assert_eq!(policy.after_run(Ended::GpuChanged, false, now), Next::GpuChanged);
        }
        assert_eq!(policy.after_run(Ended::Stopped, false, now), Next::Stop);
        assert_eq!(
            policy.after_run(failure("failed"), false, now),
            Next::Restart { attempt: 1, error: "failed".into() }
        );
    }
}
