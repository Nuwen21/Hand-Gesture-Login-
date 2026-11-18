from getpass import getpass

from database import (
    init_db,
    create_user,
    get_user,
    is_locked,
    lock_remaining_seconds,
    record_failed_attempt,
    reset_failed_attempts,
    log_login,
    show_logs,
)
from gesture_detector import capture_gesture_sequence, sequence_to_string
from security import hash_secret, verify_secret

GESTURE_LENGTH = 3


def register_user():
    print("\n--- Register User ---")
    username = input("Enter username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    password = getpass("Enter password: ")
    confirm = getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.")
        return

    print("\nNow create your gesture password.")
    print("Use 3 gestures. Example: 5 -> 0 -> 2")
    print("Gesture values: 0=fist, 1=one finger, 2=two fingers, 3=three fingers, 4=four fingers, 5=open palm")

    sequence = capture_gesture_sequence(sequence_length=GESTURE_LENGTH)
    if sequence is None:
        print("Gesture registration cancelled.")
        return

    gesture_string = sequence_to_string(sequence)
    password_salt, password_hash = hash_secret(password)
    gesture_salt, gesture_hash = hash_secret(gesture_string)

    if create_user(username, password_salt, password_hash, gesture_salt, gesture_hash):
        log_login(username, "REGISTERED", f"gesture_length={GESTURE_LENGTH}")
        print(f"User registered successfully. Gesture saved as a secure hash. Captured sequence: {gesture_string}")
    else:
        print("Username already exists.")


def login_user():
    print("\n--- Login ---")
    username = input("Enter username: ").strip()
    user = get_user(username)

    if user is None:
        log_login(username, "FAILED", "unknown username")
        print("Login failed.")
        return

    if is_locked(user):
        seconds = lock_remaining_seconds(user)
        log_login(username, "FAILED", "account locked")
        print(f"Account is temporarily locked. Try again in {seconds} seconds.")
        return

    password = getpass("Enter password: ")
    if not verify_secret(password, user["password_salt"], user["password_hash"]):
        record_failed_attempt(username)
        log_login(username, "FAILED", "wrong password")
        print("Login failed.")
        return

    print("\nPassword correct. Now perform your 3 gesture sequence.")
    sequence = capture_gesture_sequence(sequence_length=GESTURE_LENGTH)
    if sequence is None:
        log_login(username, "FAILED", "gesture cancelled")
        print("Login cancelled.")
        return

    gesture_string = sequence_to_string(sequence)
    if verify_secret(gesture_string, user["gesture_salt"], user["gesture_hash"]):
        reset_failed_attempts(username)
        log_login(username, "SUCCESS", "password and gesture matched")
        print("Login successful.")
    else:
        record_failed_attempt(username)
        log_login(username, "FAILED", "wrong gesture")
        print("Login failed. Gesture sequence did not match.")


def view_logs():
    print("\n--- Recent Login Logs ---")
    rows = show_logs()
    if not rows:
        print("No logs found.")
        return
    for row in rows:
        print(f"{row['created_at']} | {row['username']} | {row['status']} | {row['reason']}")


def main():
    init_db()

    while True:
        print("\n==============================")
        print(" Hand Gesture-Based Login System")
        print("==============================")
        print("1. Register")
        print("2. Login")
        print("3. View Login Logs")
        print("4. Exit")

        choice = input("Choose option: ").strip()

        if choice == "1":
            register_user()
        elif choice == "2":
            login_user()
        elif choice == "3":
            view_logs()
        elif choice == "4":
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()
