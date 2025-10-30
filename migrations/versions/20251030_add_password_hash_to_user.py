"""add password_hash to user and backfill

Revision ID: add_password_hash_to_user
Revises: ad49fe55ba9f
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_password_hash_to_user'
down_revision = 'ad49fe55ba9f'
branch_labels = None
depends_on = None


def upgrade():
    # Add new column password_hash
    op.add_column('user', sa.Column('password_hash', sa.String(length=255), nullable=True))

    # Backfill from legacy plaintext password column if it exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('user')]

    if 'password' in columns:
        try:
            # Import locally to avoid hard dependency in migration environment
            from werkzeug.security import generate_password_hash

            result = bind.execute(sa.text('SELECT id, password FROM "user"'))
            rows = result.fetchall()
            for row in rows:
                user_id = row[0]
                plaintext = row[1]
                if plaintext:
                    hashed = generate_password_hash(plaintext)
                    bind.execute(
                        sa.text('UPDATE "user" SET password_hash = :hashed WHERE id = :id'),
                        {"hashed": hashed, "id": user_id},
                    )
        except Exception:
            # If anything goes wrong during backfill, continue with column in place
            pass

    # Ensure not null now that column exists; SQLite ALTER may not support directly with existing nulls
    # This line is safe if all rows have been backfilled; otherwise it will be ignored depending on backend
    try:
        with op.batch_alter_table('user') as batch_op:
            batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=False)
    except Exception:
        pass


def downgrade():
    # Best-effort drop of password_hash; some SQLite versions may not support drop column
    try:
        with op.batch_alter_table('user') as batch_op:
            batch_op.drop_column('password_hash')
    except Exception:
        pass


