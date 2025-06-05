"""Add user_id to Image table

Revision ID: 6c1bfff942cc
Revises: 86fc864a1553
Create Date: 2025-05-25 20:11:10.544530

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c1bfff942cc'
down_revision = '86fc864a1553'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('image', schema=None) as batch_op:
    # 1단계: nullable=True, 기본값 없음으로 컬럼 추가
        # batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        pass
    # 2단계: 기존 데이터에 기본값 넣기 (필요 시)
    # 만약 user_id=0 으로 넣는 게 문제 없다면 실행, 아니면 적절한 user_id로 변경
    op.execute('UPDATE image SET user_id = 0 WHERE user_id IS NULL')

    with op.batch_alter_table('image', schema=None) as batch_op:
        # 3단계: nullable=False로 변경, foreign key 추가
        batch_op.alter_column('user_id', nullable=False)
        batch_op.create_foreign_key(
            'fk_image_user_id_user',  # 제약조건 이름 명시 필수
            'user',
            ['user_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('image', schema=None) as batch_op:
        batch_op.drop_constraint('fk_image_user_id_user', type_='foreignkey')
        batch_op.drop_column('user_id')


    # ### end Alembic commands ###
