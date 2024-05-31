"""Add reference table

Revision ID: 23afcfd1d789
Revises: cff0aef2c0f7
Create Date: 2024-05-30 18:29:17.581830

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "23afcfd1d789"
down_revision = "cff0aef2c0f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "reference",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=4096), nullable=True),
        sa.Column("vulnerability_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["vulnerability_id"],
            ["vulnerability.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("agent_argument", schema=None) as batch_op:
        batch_op.alter_column(
            "value", existing_type=sa.BLOB(), type_=sa.Text(), existing_nullable=True
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("agent_argument", schema=None) as batch_op:
        batch_op.alter_column(
            "value", existing_type=sa.Text(), type_=sa.BLOB(), existing_nullable=True
        )

    op.drop_table("reference")
    # ### end Alembic commands ###
