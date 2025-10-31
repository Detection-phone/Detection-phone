"""Add weekly schedule settings

Revision ID: add_weekly_schedule
Revises: add_password_hash_to_user
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = 'add_weekly_schedule'
down_revision = 'add_password_hash_to_user'
branch_labels = None
depends_on = None

# Default weekly schedule structure (Mon-Fri 7:00-16:00, weekends off)
DEFAULT_SCHEDULE = {
    'monday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'tuesday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'wednesday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'thursday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'friday': {'enabled': True, 'start': '07:00', 'end': '16:00'},
    'saturday': {'enabled': False, 'start': '07:00', 'end': '16:00'},
    'sunday': {'enabled': False, 'start': '07:00', 'end': '16:00'}
}

def upgrade():
    # Check if settings table already exists (for manual resets)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'settings' in existing_tables:
        print("⚠️  Tabela 'settings' już istnieje - pomijam tworzenie")
        # Optionally, you could update the existing table here if needed
        return
    
    # Create Settings table with weekly schedule JSON field
    # SQLite stores JSON as TEXT, so we use String type for compatibility
    op.create_table('settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('schedule', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default settings record
    schedule_json = json.dumps(DEFAULT_SCHEDULE)
    bind.execute(
        sa.text("INSERT INTO settings (schedule, created_at, updated_at) VALUES (:schedule, datetime('now'), datetime('now'))"),
        {"schedule": schedule_json}
    )


def downgrade():
    # Drop Settings table
    op.drop_table('settings')

