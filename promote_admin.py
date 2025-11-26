import sys
from store import store

def promote_to_admin(username: str) -> None:
    username = username.strip().lower()
    
    if not username:
        print("Ошибка: Укажите имя пользователя")
        sys.exit(1)
    
    user = store.get_user_by_username(username)
    if not user:
        print(f"Ошибка: Пользователь '{username}' не найден")
        sys.exit(1)
    
    if user.role == "admin":
        print(f"Пользователь '{username}' уже является администратором")
        sys.exit(0)
    
    user.role = "admin"

    store._save_user_to_db(user)

    store.reload_user_from_db(user.user_id)
    
    print(f"✓ Пользователю '{username}' успешно выданы права администратора")
    print(f"  User ID: {user.user_id}")
    print(f"  Роль: {user.role}")
    print(f"\n⚠️  Внимание: Пользователю нужно переавторизоваться для применения изменений!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python promote_admin.py <username>")
        print("\nПример:")
        print("  python promote_admin.py myuser")
        sys.exit(1)
    
    username = sys.argv[1]
    promote_to_admin(username)

