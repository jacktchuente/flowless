import {Component, Inject, OnInit} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from "@angular/material/dialog";
import {MatButtonModule} from "@angular/material/button";
import {TranslateModule} from "@ngx-translate/core";
import {DialogTemplate1Component} from "@project-shared/templates/dialog-template1/dialog-template1.component";
import {MatIconModule} from "@angular/material/icon";

@Component({
  standalone: true,
  selector: 'confirmation1',
  templateUrl: './confirmation-dialog.component.html',
  imports: [
    MatButtonModule,
    TranslateModule,
    DialogTemplate1Component,
    MatDialogModule,
    MatIconModule
  ],
  styleUrls: ['./confirmation-dialog.component.css']
})
export class ConfirmationDialogComponent implements OnInit {

  confirmationMessage = 'Cette action est irreversible. Voulez-vous vraiment continuer ?';

  constructor(
    public dialogRef: MatDialogRef<ConfirmationDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any) {
    if (Object.keys(data).indexOf('confirmationMessage') > -1 && data.confirmationMessage) {
      this.confirmationMessage = data.confirmationMessage;
    }
  }

  ngOnInit() {
  }

  cancel(): void {
    this.dialogRef.close(false);
  }

  confirm(): void {
    this.dialogRef.close(true);
  }
}
