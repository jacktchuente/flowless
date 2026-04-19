import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DialogContainer1Component } from './dialog-container1.component';

describe('DialogContainer1Component', () => {
  let component: DialogContainer1Component;
  let fixture: ComponentFixture<DialogContainer1Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DialogContainer1Component]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DialogContainer1Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
