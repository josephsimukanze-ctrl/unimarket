from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        (
            "accounts",
            "0004_user_avatar_user_bio_user_city_user_country_and_more",
        ),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE accounts_user
                ADD COLUMN username varchar(150);

                UPDATE accounts_user
                SET username = 'user_' || replace(id::text, '-', '')
                WHERE username IS NULL;

                ALTER TABLE accounts_user
                ALTER COLUMN username SET NOT NULL;

                ALTER TABLE accounts_user
                ADD CONSTRAINT accounts_user_username_key
                UNIQUE (username);
            """,
            reverse_sql="""
                ALTER TABLE accounts_user
                DROP CONSTRAINT IF EXISTS accounts_user_username_key;

                ALTER TABLE accounts_user
                DROP COLUMN IF EXISTS username;
            """,
        ),
    ]
