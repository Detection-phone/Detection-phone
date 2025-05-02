"""Initial migration

Revision ID: 2c71483e22ea
Revises: 
Create Date: 2024-02-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash


# revision identifiers, used by Alembic.
revision = '2c71483e22ea'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing tables if they exist
    op.drop_table('detection', if_exists=True)
    op.drop_table('user', if_exists=True)
    op.drop_table('settings', if_exists=True)

    # Create tables
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    op.create_table(
        'detection',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('image_path', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_detection_user_id'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=True),
        sa.Column('description', sa.String(length=200), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )

    op.create_index('ix_detection_timestamp', 'detection', ['timestamp'], unique=False)

    # Create default admin user
    connection = op.get_bind()
    connection.execute(
        sa.text("INSERT INTO user (username, password_hash, role) VALUES (:username, :password_hash, :role)"),
        {
            'username': 'admin',
            'password_hash': generate_password_hash('admin123'),
            'role': 'admin'
        }
    )


def downgrade():
    op.drop_index('ix_detection_timestamp', table_name='detection')
    op.drop_table('detection')
    op.drop_table('user')
    op.drop_table('settings')
