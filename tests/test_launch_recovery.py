"""Exercise stalled relaunch helpers and authentication sockets without iOS."""

from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / "source" / "Showcase.m").read_text()
wait = source[source.index("static void reap_child("):
              source.index("static NSData *capture_process_output(")]
harness = r"""
#include <assert.h>
#include <signal.h>
#include <stdio.h>
#include <sys/wait.h>
#include <time.h>
#include "baa_broker.h"

static uint64_t monotonic_nanos_now(void) {
    struct timespec now;
    assert(clock_gettime(CLOCK_MONOTONIC, &now) == 0);
    return (uint64_t)now.tv_sec * 1000000000 + now.tv_nsec;
}

#define QOS_CLASS_UTILITY 0
#define dispatch_get_global_queue(qos, flags) (0)
static void (*pending_reap)(void *);
static void *reap_context;
static void dispatch_async_f(int queue, void *context, void (*work)(void *)) {
    (void)queue;
    pending_reap = work;
    reap_context = context;
}
""" + wait + r"""
static void test_children(void) {
    pid_t pid = fork();
    assert(pid >= 0);
    if (!pid) _exit(42);
    int status = wait_child_bounded(pid, monotonic_nanos_now() + 1000000000);
    assert(status >= 0 && WIFEXITED(status) && WEXITSTATUS(status) == 42);
    assert(!pending_reap);

    pid = fork();
    assert(pid >= 0);
    if (!pid) for (;;) pause();
    uint64_t now = monotonic_nanos_now();
    assert(wait_child_bounded(pid, now + 100000000) == -1);
    assert(errno == ETIMEDOUT);
    assert(monotonic_nanos_now() - now < 1000000000);
    assert(pending_reap);
    pending_reap(reap_context);
    assert(waitpid(pid, NULL, WNOHANG) == -1 && errno == ECHILD);
}

static void test_broker(void) {
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    int client = sockets[0], peer = sockets[1];
    assert(baa_socket_timeout(client) && baa_socket_timeout(peer));
    assert(baa_write_exact(client, "hello", 5));
    char buffer[5];
    assert(baa_read_exact(peer, buffer, sizeof(buffer)));
    assert(memcmp(buffer, "hello", sizeof(buffer)) == 0);

    /* Leave both peers open but silent. Neither should hang on a read. */
    uint64_t now = monotonic_nanos_now();
    assert(!baa_read_exact(client, buffer, sizeof(buffer)));
    assert(monotonic_nanos_now() - now < 4000000000);
    now = monotonic_nanos_now();
    assert(!baa_read_exact(peer, buffer, sizeof(buffer)));
    assert(monotonic_nanos_now() - now < 4000000000);
    close(peer);
    close(client);
}

int main(void) {
    test_children();
    test_broker();
    puts("PASS: bounded child recovery, successful BAA exchange and stalled BAA peers");
}
"""

with tempfile.TemporaryDirectory(prefix="showcase-recovery-") as directory:
    path = Path(directory)
    (path / "test.c").write_text(harness)
    subprocess.run(["clang", "-Wall", "-Wextra", "-Werror", "-I", str(root / "source"), str(path / "test.c"),
                    "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], cwd=path, check=True, timeout=12)
